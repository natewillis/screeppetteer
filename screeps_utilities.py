import re
import screepsapi
import configparser
import constants

# logging
import logging
logger = logging.getLogger(__name__)


def create_screep_id(id="unknown", name="unknown", type="unknown"):
    return f'{type}|{name}|{id}'


def js_row_col_to_room(js_row_col):

    # define variables
    js_row = js_row_col['row']
    js_col = js_row_col['col']

    # calc row
    if js_row < 0:
        room_row = abs(js_row) - 1
        n_s = 'S'
    else:
        room_row = js_row
        n_s = 'N'

    # calc col
    if js_col < 0:
        room_col = abs(js_col) - 1
        e_w = 'W'
    else:
        room_col = js_col
        e_w = 'E'

    return f'{e_w}{room_col}{n_s}{room_row}'


def js_room_row_col(room_name):
    # E0N0 is 0,0
    # init return variables
    # its better to ask forgiveness than permission
    try:

        # do regexp
        matches = re.search(r'([WE])(\d+)([NS])(\d+)', room_name.upper())

        # calc row
        row = abs(int(matches.group(4)))
        if matches.group(3) == 'S':
            row = (row + 1) * -1

        # calc col
        col = abs(int(matches.group(2)))
        if matches.group(1) == 'W':
            col = (col + 1) * -1

    except AttributeError:

        # no match
        row = None
        col = None

    return {'row': row, 'col': col}


def create_api_connection(user, password, host=None):
    # init api
    api = None

    # login to public servers with no host
    if host is None:
        logger.info(f'no host was provided so connecting to main servers as {user}')
        api = screepsapi.API(u=user, p=password)
    else:  # login to private host
        logger.info(f'connecting to {host} as {user}')
        api = screepsapi.API(u=user, p=password, host=host)

    # return the  api
    return api


def create_api_connection_from_config(config_file_location):
    # get username and password from safe file
    config = configparser.ConfigParser()
    config.read(config_file_location)

    # server data
    user = config['CONNECTION']['user']
    password = config['CONNECTION']['password']
    host = config['CONNECTION']['host'] if 'host' in config['CONNECTION'] else None

    # return connection
    logger.info(f'creating api connection for {user} at {host}')
    return create_api_connection(host=host, user=user, password=password)


def creep_body_resource_cost(body):
    cost = 0
    for part in body:
        cost += constants.CREEP_BODY_PART_COST[part]
    return cost


def creep_body_spawn_time(body):
    return len(body) * constants.CREEP_SPAWN_TIME


def delta_from_direction(direction):
    if direction == constants.TOP:
        delta = {'x': 0, 'y': 1}
    elif direction == constants.TOP_RIGHT:
        delta = {'x': 1, 'y': 1}
    elif direction == constants.RIGHT:
        delta = {'x': 1, 'y': 0}
    elif direction == constants.BOTTOM_RIGHT:
        delta = {'x': 1, 'y': -1}
    elif direction == constants.BOTTOM:
        delta = {'x': 0, 'y': -1}
    elif direction == constants.BOTTOM_LEFT:
        delta = {'x': -1, 'y': -1}
    elif direction == constants.LEFT:
        delta = {'x': -1, 'y': 0}
    elif direction == constants.TOP_LEFT:
        delta = {'x': -1, 'y': 1}
    return delta


def edge_of_room():
    pass


def is_edge_of_room_from_terrain_index(terrain_index):

    # calculate row from the top
    local_y_from_top = (terrain_index // 50)
    local_x = (terrain_index - (local_y_from_top * 50))

    # if logic
    if local_y_from_top == 0 or local_y_from_top == 49 or local_x == 0 or local_x == 49:
        return True
    else:
        return False
