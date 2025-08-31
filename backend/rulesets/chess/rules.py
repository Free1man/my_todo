from __future__ import annotations
from typing import Dict, Optional, Any, List
from copy import deepcopy
from backend.core.primitives import Explanation
from .models import State, Piece, PieceType, Color


Files='abcdefgh'; Ranks='12345678'
DIRS_KNIGHT=[(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]
DIRS_BISHOP=[(1,1),(1,-1),(-1,1),(-1,-1)]
DIRS_ROOK=[(1,0),(-1,0),(0,1),(0,-1)]
DIRS_KING=DIRS_BISHOP+DIRS_ROOK


def opposite(c:Color)->Color: return 'black' if c=='white' else 'white'


def initial_board()->Dict[str,Piece]:
    def P(t:PieceType,c:Color): return Piece(type=t,color=c)
    b:Dict[str,Piece]={}
    for f in Files: b[f+'2']=P('pawn','white'); b[f+'7']=P('pawn','black')
    back=[('a','rook'),('b','knight'),('c','bishop'),('d','queen'),('e','king'),('f','bishop'),('g','knight'),('h','rook')]
    for f,t in back: b[f+'1']=P(t,'white'); b[f+'8']=P(t,'black')
    return b


def a2xy(sq:str)->tuple[int,int]: return (Files.index(sq[0]), Ranks.index(sq[1]))
def xy2a(x:int,y:int)->str: return Files[x]+Ranks[y]


def path_clear(st:State,x:int,y:int,dx:int,dy:int,x2:int,y2:int)->bool:
    cx,cy=x+dx,y+dy
    while (cx,cy)!=(x2,y2):
        if xy2a(cx,cy) in st.board: return False
        cx+=dx; cy+=dy
    return True


def square_attacked(st:State,sq:str,by:Color)->bool:
    x2,y2=a2xy(sq)
    for s,p in st.board.items():
        if p.color!=by: continue
        x,y=a2xy(s); t=p.type
        if t=='pawn':
            dir=1 if by=='white' else -1
            for dx in (-1,1):
                if (x+dx,y+dir)==(x2,y2): return True
        elif t=='knight':
            for dx,dy in DIRS_KNIGHT:
                if (x+dx,y+dy)==(x2,y2): return True
        elif t in ('bishop','rook','queen'):
            dirs=[]; 
            if t in ('bishop','queen'): dirs+=DIRS_BISHOP
            if t in ('rook','queen'): dirs+=DIRS_ROOK
            for dx,dy in dirs:
                cx,cy=x+dx,y+dy
                while 0<=cx<8 and 0<=cy<8:
                    if (cx,cy)==(x2,y2): return True
                    if xy2a(cx,cy) in st.board: break
                    cx+=dx; cy+=dy
        elif t=='king':
            for dx,dy in DIRS_KING:
                if (x+dx,y+dy)==(x2,y2): return True
    return False


def in_check(st:State,side:Color)->bool:
    ksq=next((s for s,p in st.board.items() if p.color==side and p.type=='king'), None)
    return bool(ksq and square_attacked(st, ksq, opposite(side)))


def legal_basic(st:State,src:str,dst:str,promo:Optional[PieceType]):
    info={'src':src,'dst':dst}
    if src==dst: return False, {'reason':'same square'}
    p=st.board.get(src)
    if not p: return False, {'reason':'no piece at src'}
    if p.color!=st.turn: return False, {'reason':'not your turn'}
    tgt=st.board.get(dst)
    x,y=a2xy(src); x2,y2=a2xy(dst); dx,dy=x2-x,y2-y
    if tgt and tgt.color==p.color: return False, {'reason':'friendly on dst'}

    if p.type=='pawn':
        dir=1 if p.color=='white' else -1
        start=1 if p.color=='white' else 6
        last=7 if p.color=='white' else 0
        if dx==0:
            if y2-y==dir and not tgt:
                info['kind']='normal'
            elif y==start and y2-y==2*dir and not tgt:
                mid=xy2a(x,y+dir)
                if mid in st.board: return False, {'reason':'blocked mid'}
                info['kind']='normal'; info['set_en_passant']=xy2a(x,y+dir)
            else:
                return False, {'reason':'illegal pawn advance'}
        elif abs(dx)==1 and y2-y==dir:
            if tgt and tgt.color!=p.color:
                info['kind']='capture'; info['captured_at']=dst
            elif st.en_passant==dst:
                victim=xy2a(x2,y); v=st.board.get(victim)
                if v and v.type=='pawn' and v.color!=p.color:
                    info['kind']='en_passant'; info['captured_at']=victim
                else:
                    return False, {'reason':'no en passant victim'}
            else:
                return False, {'reason':'no piece to capture'}
        else:
            return False, {'reason':'illegal pawn move'}
        if y2==last:
            info['promotion']=promo or 'queen'
            info.setdefault('kind','promotion')

    elif p.type=='knight':
        if (abs(dx),abs(dy)) in [(1,2),(2,1)]: info['kind']='capture' if tgt else 'normal'
        else: return False, {'reason':'illegal knight'}

    elif p.type=='bishop':
        if abs(dx)==abs(dy) and path_clear(st,x,y,1 if dx>0 else -1,1 if dy>0 else -1,x2,y2):
            info['kind']='capture' if tgt else 'normal'
        else: return False, {'reason':'illegal bishop/path'}

    elif p.type=='rook':
        if (dx==0 or dy==0) and path_clear(st,x,y,0 if dx==0 else (1 if dx>0 else -1),0 if dy==0 else (1 if dy>0 else -1),x2,y2):
            info['kind']='capture' if tgt else 'normal'
        else: return False, {'reason':'illegal rook/path'}

    elif p.type=='queen':
        if ((abs(dx)==abs(dy)) or (dx==0 or dy==0)):
            sx=0 if dx==0 else (1 if dx>0 else -1); sy=0 if dy==0 else (1 if dy>0 else -1)
            if path_clear(st,x,y,sx,sy,x2,y2):
                info['kind']='capture' if tgt else 'normal'
            else:
                return False, {'reason':'path blocked'}
        else:
            return False, {'reason':'illegal queen'}

    elif p.type=='king':
        if max(abs(dx),abs(dy))==1:
            info['kind']='capture' if tgt else 'normal'
        elif p.color=='white' and src=='e1' and y2==0 and x2 in (6,2):
            if x2==6:
                if not st.castle_K: return False, {'reason':'no K right'}
                if any(s in st.board for s in ('f1','g1')): return False, {'reason':'blocked'}
                if in_check(st,'white') or square_attacked(st,'f1','black') or square_attacked(st,'g1','black'): return False, {'reason':'through check'}
                info['kind']='castle_k'
            else:
                if not st.castle_Q: return False, {'reason':'no Q right'}
                if any(s in st.board for s in ('b1','c1','d1')): return False, {'reason':'blocked'}
                if in_check(st,'white') or square_attacked(st,'d1','black') or square_attacked(st,'c1','black'): return False, {'reason':'through check'}
                info['kind']='castle_q'
        elif p.color=='black' and src=='e8' and y2==7 and x2 in (6,2):
            if x2==6:
                if not st.castle_k: return False, {'reason':'no k right'}
                if any(s in st.board for s in ('f8','g8')): return False, {'reason':'blocked'}
                if in_check(st,'black') or square_attacked(st,'f8','white') or square_attacked(st,'g8','white'): return False, {'reason':'through check'}
                info['kind']='castle_k'
            else:
                if not st.castle_q: return False, {'reason':'no q right'}
                if any(s in st.board for s in ('b8','c8','d8')): return False, {'reason':'blocked'}
                if in_check(st,'black') or square_attacked(st,'d8','white') or square_attacked(st,'c8','white'): return False, {'reason':'through check'}
                info['kind']='castle_q'
        else:
            return False, {'reason':'illegal king'}

    return True, info


def _apply_basic(st:State,src:str,dst:str,info:Dict[str,Any]):
    p=st.board.pop(src)
    cap_at=info.get('captured_at')
    if cap_at: st.board.pop(cap_at, None); st.halfmove_clock=0
    st.en_passant=info.get('set_en_passant')
    if p.type=='pawn' or cap_at: st.halfmove_clock=0
    else: st.halfmove_clock+=1
    promo=info.get('promotion')
    st.board[dst]=Piece(type=promo, color=p.color) if promo else p  # type: ignore

    if info.get('kind')=='castle_k':
        if p.color=='white':
            if 'h1' in st.board: st.board['f1']=st.board.pop('h1')
            st.castle_K=st.castle_Q=False
        else:
            if 'h8' in st.board: st.board['f8']=st.board.pop('h8')
            st.castle_k=st.castle_q=False
    elif info.get('kind')=='castle_q':
        if p.color=='white':
            if 'a1' in st.board: st.board['d1']=st.board.pop('a1')
            st.castle_K=st.castle_Q=False
        else:
            if 'a8' in st.board: st.board['d8']=st.board.pop('a8')
            st.castle_k=st.castle_q=False

    if p.type=='king':
        if p.color=='white': st.castle_K=st.castle_Q=False
        else: st.castle_k=st.castle_q=False
    if p.type=='rook':
        if src=='h1': st.castle_K=False
        if src=='a1': st.castle_Q=False
        if src=='h8': st.castle_k=False
        if src=='a8': st.castle_q=False

    st.turn = opposite(st.turn)
    if st.turn == 'white': st.fullmove_number += 1


def explain_move(st:State,src:str,dst:str,promo:Optional[PieceType]=None)->Explanation:
    steps=[]
    if src not in st.board: return Explanation(ok=False, steps=[{"check":"piece_at_src","ok":False}])
    steps.append({"check":"turn","ok": st.board[src].color == st.turn})
    ok,info=legal_basic(st,src,dst,promo)
    steps.append({"check":"basic_legality","ok":ok,"info":info})
    if not ok: return Explanation(ok=False, steps=steps, outcome={"reason":info.get("reason")})
    g2=deepcopy(st); _apply_basic(g2,src,dst,info)
    side_moved='white' if g2.turn=='black' else 'black'
    self_check=in_check(g2, side_moved)
    steps.append({"check":"self_check_after_move","ok": not self_check})
    opp_in_check=in_check(g2, g2.turn)
    return Explanation(ok=not self_check, steps=steps, outcome={"kind":info.get("kind"),"promotion":info.get("promotion"),"opponent_in_check":opp_in_check})


def apply_move(st:State,src:str,dst:str,promo:Optional[PieceType]=None)->dict:
    ok,info=legal_basic(st,src,dst,promo)
    if not ok: return {"ok":False,"error":info.get("reason")}
    g2=deepcopy(st); _apply_basic(g2,src,dst,info)
    side_moved='white' if g2.turn=='black' else 'black'
    if in_check(g2, side_moved): return {"ok":False,"error":"move leaves king in check"}
    _apply_basic(st,src,dst,info)
    return {"ok": True}


def has_any_legal_move(st:State, side:Color)->bool:
    for src,p in list(st.board.items()):
        if p.color!=side: continue
        for f in Files:
            for r in Ranks:
                dst=f+r
                ok,info=legal_basic(st,src,dst,None)
                if not ok: continue
                g2=deepcopy(st); _apply_basic(g2,src,dst,info)
                if not in_check(g2, side): return True
    return False


def summarize(st:State)->dict:
    if st.halfmove_clock>=100: st.status='draw'; st.winner=None; return {"status":st.status, "winner":st.winner}
    side=st.turn
    if in_check(st,side) and not has_any_legal_move(st,side): st.status='checkmate'; st.winner=opposite(side); return {"status":st.status,"winner":st.winner}
    if not in_check(st,side) and not has_any_legal_move(st,side): st.status='stalemate'; st.winner=None; return {"status":st.status,"winner":st.winner}
    return {"status":st.status, "winner":st.winner, "turn":st.turn, "fullmove":st.fullmove_number}
