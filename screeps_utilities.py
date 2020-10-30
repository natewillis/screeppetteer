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


def room_js_row_col(room_name):
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
