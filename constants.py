

# resource info
RESOURCES = ['energy', 'power', 'H', 'O', 'U', 'L', 'K', 'Z', 'X', 'G']

# creep info
CREEP_BODY_PARTS = ['move', 'work', 'carry', 'attack', 'range_attack', 'tough', 'heal', 'claim']
CREEP_BODY_PART_COST = {
    "move": 50,
    "work": 100,
    "attack": 80,
    "carry": 50,
    "heal": 250,
    "ranged_attack": 150,
    "tough": 10,
    "claim": 600
}
CREEP_LIFE_TIME = 1500
CARRY_CAPACITY = 50
HARVEST_POWER = 2
HARVEST_MINERAL_POWER = 1
HARVEST_DEPOSIT_POWER = 1
REPAIR_POWER = 100
DISMANTLE_POWER = 50
BUILD_POWER = 5
ATTACK_POWER = 30
UPGRADE_CONTROLLER_POWER = 1
RANGED_ATTACK_POWER = 10
HEAL_POWER = 12
RANGED_HEAL_POWER = 4
REPAIR_COST = 0.01
DISMANTLE_COST = 0.005
BASIC_UTILITY_CREEP = ['carry', 'work', 'move', 'move']
BASIC_DELIVERY_CREEP = ['carry', 'move']
HARVEST_CREEP = ['work', 'work', 'work', 'work', 'work', 'move']

# spawn constants
SPAWN_HITS = 5000
SPAWN_ENERGY_START = 300
SPAWN_ENERGY_CAPACITY = 300
CREEP_SPAWN_TIME = 3
SPAWN_RENEW_RATIO = 1.2

# colors
COLOR_RED = 1
COLOR_PURPLE = 2
COLOR_BLUE = 3
COLOR_CYAN = 4
COLOR_GREEN = 5
COLOR_YELLOW = 6
COLOR_ORANGE = 7
COLOR_BROWN = 8
COLOR_GREY = 9
COLOR_WHITE = 10


# direction constants
TOP = 1
TOP_RIGHT = 2
RIGHT = 3
BOTTOM_RIGHT = 4
BOTTOM = 5
BOTTOM_LEFT = 6
LEFT = 7
TOP_LEFT = 8