# backend/core/templates.py
from __future__ import annotations
from typing import Any, get_args, get_origin, Literal, Union
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

# typed fallbacks if a field has no default
def _fallback_for_type(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin is Literal:
        return get_args(tp)[0]
    if origin in (list, tuple, set, frozenset):
        args = get_args(tp)
        return [ _fallback_for_type(args[0]) ] if args else []
    if origin in (dict,):
        return {}
    if origin in (Union,):
        # try first non-None arg
        args = [a for a in get_args(tp) if a is not type(None)]
        return _fallback_for_type(args[0]) if args else None
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return build_template(tp)
    # primitives
    if tp in (int,): return 0
    if tp in (float,): return 0.0
    if tp in (bool,): return False
    if tp in (str,): return "string"
    return None

def build_template(model_cls: type[BaseModel]) -> dict:
    """
    Build a dict template for a Pydantic model using its defaults where present,
    falling back to typed placeholders, recursing into nested models.
    """
    out: dict[str, Any] = {}
    for name, f in model_cls.model_fields.items():
        if f.default is not PydanticUndefined:
            val = f.default
        elif f.default_factory is not None:
            val = f.default_factory()
        else:
            val = _fallback_for_type(f.annotation)

        if isinstance(val, BaseModel):
            val = val.model_dump()
        elif isinstance(val, list) and val and isinstance(val[0], BaseModel):
            val = [v.model_dump() for v in val]
        out[name] = val
    # validate once to normalize shapes (e.g., Pos etc.)
    try:
        return model_cls.model_validate(out).model_dump()
    except Exception:
        return out

def model_schema(model_cls: type[BaseModel]) -> dict:
    return model_cls.model_json_schema()
