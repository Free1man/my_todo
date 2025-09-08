from ..models.enums import Side, StatName, Terrain
from ..models.map import MapGrid, Tile
from ..models.mission import GoalKind, Mission, MissionEvent, MissionGoal
from ..models.modifiers import ModifierSource, Operation, StatBlock, StatModifier
from ..models.skills import Item, Skill, SkillKind, SkillTarget
from ..models.units import Unit


def default_demo_mission() -> Mission:
    width, height = 8, 8
    # Start with plains
    terrain = [[Terrain.PLAIN for _ in range(width)] for _ in range(height)]
    # Horizontal river at y == 3 with a 2-tile bridge at x == 3..4
    for x in range(width):
        terrain[3][x] = Terrain.WATER
    terrain[3][3] = Terrain.PLAIN
    terrain[3][4] = Terrain.PLAIN

    # Add some forests (defensive cover) and hills (high ground)
    forests = {(1, 0), (2, 0), (1, 1), (6, 2), (0, 5), (1, 5)}
    hills = {(6, 1), (2, 5), (5, 6)}
    blocked = {(0, 7)}  # a small rock outcrop that's impassable
    for x, y in forests:
        terrain[y][x] = Terrain.FOREST
    for x, y in hills:
        terrain[y][x] = Terrain.HILL
    for x, y in blocked:
        terrain[y][x] = Terrain.BLOCKED

    grid = MapGrid(
        width=width,
        height=height,
        tiles=[
            [Tile(terrain=terrain[y][x], mods=[]) for x in range(width)]
            for y in range(height)
        ],
    )

    iron_sword = Item(
        id="item.sword",
        name="Iron Sword",
        mods=[
            StatModifier(
                stat=StatName.ATK,
                operation=Operation.ADDITIVE,
                value=2,
                source=ModifierSource.ITEM,
            )
        ],
    )
    leather_armor = Item(
        id="item.armor",
        name="Leather Armor",
        mods=[
            StatModifier(
                stat=StatName.DEF,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.ITEM,
            )
        ],
    )

    passive_focus = Skill(
        id="skill.passive.focus",
        name="Keen Focus",
        kind=SkillKind.PASSIVE,
        passive_mods=[
            StatModifier(
                stat=StatName.CRIT,
                operation=Operation.ADDITIVE,
                value=10,
                source=ModifierSource.SKILL,
            )
        ],
    )
    active_shout = Skill(
        id="skill.active.shout",
        name="War Shout",
        kind=SkillKind.ACTIVE,
        ap_cost=1,
        range=2,
        target=SkillTarget.ALLY_UNIT,
        apply_mods=[
            StatModifier(
                stat=StatName.ATK,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.SKILL,
                duration_turns=2,
            )
        ],
        cooldown=2,
    )

    heal = Skill(
        id="skill.active.heal",
        name="Heal",
        kind=SkillKind.ACTIVE,
        ap_cost=1,
        range=3,
        target=SkillTarget.ALLY_UNIT,
        apply_mods=[
            StatModifier(
                stat=StatName.HP,
                operation=Operation.ADDITIVE,
                value=4,
                source=ModifierSource.SKILL,
            )
        ],
        cooldown=1,
    )

    fireball = Skill(
        id="skill.active.fireball",
        name="Fireball",
        kind=SkillKind.ACTIVE,
        ap_cost=2,
        range=4,
        target=SkillTarget.TILE,
        apply_mods=[
            StatModifier(
                stat=StatName.HP,
                operation=Operation.ADDITIVE,
                value=-3,
                source=ModifierSource.SKILL,
            )
        ],
        cooldown=2,
    )

    self_rally = Skill(
        id="skill.active.rally_self",
        name="Battle Trance",
        kind=SkillKind.ACTIVE,
        ap_cost=1,
        range=0,
        target=SkillTarget.SELF,
        apply_mods=[
            StatModifier(
                stat=StatName.ATK,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.SKILL,
                duration_turns=2,
            )
        ],
        cooldown=2,
    )

    units = {
        "u.fighter": Unit(
            id="u.fighter",
            side=Side.PLAYER,
            name="Fighter",
            pos=(1, 1),
            items=[iron_sword, leather_armor],
            skills=[active_shout, passive_focus],
        ),
        "u.priest": Unit(
            id="u.priest",
            side=Side.PLAYER,
            name="Priest",
            pos=(2, 1),
            skills=[heal],
        ),
        "u.mage": Unit(
            id="u.mage",
            side=Side.PLAYER,
            name="Mage",
            pos=(0, 2),
            skills=[fireball, self_rally],
        ),
        "e.goblin1": Unit(
            id="e.goblin1",
            side=Side.ENEMY,
            name="Goblin",
            pos=(5, 5),
            stats=StatBlock(
                base={
                    StatName.HP: 8,
                    StatName.AP: 2,
                    StatName.ATK: 2,
                    StatName.DEF: 0,
                    StatName.MOV: 4,
                    StatName.RNG: 1,
                    StatName.CRIT: 0,
                    StatName.INIT: 8,
                }
            ),
        ),
        "e.goblin2": Unit(
            id="e.goblin2",
            side=Side.ENEMY,
            name="Goblin",
            pos=(6, 5),
            stats=StatBlock(
                base={
                    StatName.HP: 8,
                    StatName.AP: 2,
                    StatName.ATK: 2,
                    StatName.DEF: 0,
                    StatName.MOV: 4,
                    StatName.RNG: 1,
                    StatName.CRIT: 0,
                    StatName.INIT: 7,
                }
            ),
        ),
    }

    mission = Mission(
        id="mission.demo",
        name="Demo Skirmish",
        map=grid,
        units=units,
        side_to_move=Side.PLAYER,
        turn=1,
        max_turns=20,
        goals=[MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)],
        pre_events=[
            MissionEvent(id="intro", text="Cross the river and defeat the goblins!")
        ],
        post_events=[],
        global_mods=[],
        initiative_order=[],
        current_unit_id=None,
        enemy_ai=True,
    )
    return mission
