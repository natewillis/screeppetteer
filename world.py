import networkx as nx
import configparser
from screeps_utilities import room_js_row_col, js_row_col_to_room, create_api_connection_from_config
import os
import numpy as np
import pickle
import constants

# logging
import logging
logger = logging.getLogger(__name__)


class Point:

    def __init__(self, x=0, y=0, snapshot_json=None, world=None):

        # create point from either snapshot or directly
        if snapshot_json is None:
            self.x = x
            self.y = y
        else:
            point = Room(room_name=snapshot_json['room_name'], bottom_left_js_row_col=world.bottom_left_room_js_row_col).point_from_js_pos(snapshot_json)
            self.x = point.x
            self.y = point.y

        # bottom left js row col for room operations
        self.world = world

    def convert_from_snapshot_json(self, snapshot_json):
        pass

    def __str__(self):
        return f'x:{self.x} y:{self.y}'

    def __hash__(self):
        return hash((self.x, self.y))

    def range(self, point):
        return (abs(self.x-point.x)**2 + abs(self.y-point.y)**2)**0.5

    @property
    def room(self):
        room_col = int(self.x / 50)
        room_row = int(self.y / 50)
        return Room(row=room_row, col=room_col, bottom_left_js_row_col=self.world.bottom_left_room_js_row_col)

    @property
    def room_x_y(self):

        # get room
        room = self.room

        # get relative x y centered at bottom left
        x = self.x - room.bottom_left_point.x
        y = self.y - room.bottom_left_point.y

        # get flipped y
        local_y = 50 - (y + 1)

        return {'x': x, 'y': local_y}

    @property
    def room_x(self):
        return self.room_x_y['x']

    @property
    def room_y(self):
        return self.room_x_y['y']




class Room:

    def __init__(self, row=0, col=0, room_name=None, bottom_left_js_row_col=None):

        # init properties
        self.__row = row
        self.__col = col

        # top left row col
        self.__bottom_left_js_col = 0
        self.__bottom_left_js_row = 0
        if bottom_left_js_row_col is not None:
            self.__bottom_left_js_row = bottom_left_js_row_col['row']
            self.__bottom_left_js_col = bottom_left_js_row_col['col']

        # convert room_name
        if room_name is not None:
            row_col = room_js_row_col(room_name)
            self.__row = row_col['row'] - self.__bottom_left_js_row
            self.__col = row_col['col'] - self.__bottom_left_js_col

    @property
    def row(self):
        return self.__row

    @property
    def col(self):
        return self.__col

    @property
    def js_room_name(self):
        return js_row_col_to_room({
            'row': self.__row + self.__bottom_left_js_row,
            'col': self.__col + self.__bottom_left_js_col
        })

    @property
    def bottom_left_point(self):
        return Point(x=self.col * 50, y=self.col * 50)

    def point_from_terrain_index(self, terrain_index):

        # calculate row from the top
        local_y_from_top = (terrain_index // 50)
        local_y = 50 - (local_y_from_top + 1)
        local_x = (terrain_index - (local_y_from_top * 50))

        # absolute position
        y = local_y + (self.col * 50)
        x = local_x + (self.row * 50)

        return Point(x=x, y=y)

    def __str__(self):
        return f'{self.js_room_name} object'

    def point_from_js_pos(self, snapshot_json):

        # local room position
        bottom_left_point = self.bottom_left_point
        local_y_from_top = snapshot_json['y']
        local_y = 50 - (local_y_from_top + 1)
        local_x = snapshot_json['x']

        # absolute position
        y = local_y + (self.col * 50)
        x = local_x + (self.row * 50)

        # return point object
        return Point(x=x, y=y)


class Line:

    def __init__(self, points=None):
        if points is None:
            self.points == []
        else:
            self.points = points


class Terrain:
    def __init__(self, api, bottom_left_room_js_row_col, top_right_room_js_row_col, shard='shard3'):

        # world info
        self.bottom_left_room_js_row_col = bottom_left_room_js_row_col
        self.top_right_room_js_row_col = top_right_room_js_row_col
        self.shard = shard

        # connection
        logger.info(f'terrain was sent api with host {api.host} and token {api.token}')
        self.api = api

        # cache data
        self.terrain_string_cache = {}
        self.terrain_string_pickle_path = 'data/terrain_string_cache.pickle'
        if os.path.exists(self.terrain_string_pickle_path):
            with open(self.terrain_string_pickle_path, 'rb') as handle:
                self.terrain_string_cache = pickle.load(handle)

        # terrain matrix
        self.terrain_matrix = None

        # load terrain
        self.init_terrain_map()

    def update_terrain_map_from_room(self, room):

        # get host string for keyed access of cached terrain data
        host_string = 'public' if self.api.host is None else 'local'

        # pull terrain string from cache or room
        terrain_string = ''
        if host_string in self.terrain_string_cache:
            if self.shard in self.terrain_string_cache:
                if room.js_room_name in self.terrain_string_cache:
                    terrain_string = self.terrain_string_cache[host_string][self.shard][room.js_room_name]
                    logger.info(f'pulled {room.js_room_name} from cache')

        # retrieve it since we couldn't get it from cache
        if terrain_string == '':
            # get terrain string from server
            terrain_string_req_return = self.api.room_terrain(room=room.js_room_name, shard=self.shard, encoded=True)
            terrain_string = terrain_string_req_return['terrain'][0]['terrain']

            # build terrain string cache keys if necessary
            if host_string not in self.terrain_string_cache:
                self.terrain_string_cache[host_string] = {}
            if self.shard not in self.terrain_string_cache[host_string]:
                self.terrain_string_cache[host_string][self.shard] = {}

            # store the terrain string in the cache
            self.terrain_string_cache[host_string][self.shard][room.js_room_name] = terrain_string

            # logging
            logger.info(f'pulled {room.js_room_name} from server')

        # loop through terrain string for weights
        for terrain_character_index in range(0, len(terrain_string)):
            terrain_point = room.point_from_terrain_index(terrain_character_index)
            terrain_character = terrain_string[terrain_character_index]
            terrain_weight = 255  # wall
            if terrain_character == '0':  # plain
                terrain_weight = 2
            elif terrain_character == '1':  # swamp
                terrain_weight = 10
            self.terrain_matrix[terrain_point.y, terrain_point.x] = terrain_weight

    def init_terrain_map(self):

        # define rows
        world_rows = abs(self.bottom_left_room_js_row_col['row'] - self.top_right_room_js_row_col['row']) + 1
        world_cols = abs(self.bottom_left_room_js_row_col['col'] - self.top_right_room_js_row_col['col']) + 1

        # init numpy array
        logger.info(f'world has rows {world_rows} and cols {world_cols}')
        self.terrain_matrix = np.zeros((world_rows * 50, world_cols * 50), dtype=np.intc)

        # loop through rows
        for world_row in range(0, world_rows):
            for world_col in range(0, world_cols):
                world_room = Room(row=world_row, col=world_col, bottom_left_js_row_col = self.bottom_left_room_js_row_col)
                self.update_terrain_map_from_room(world_room)

        # save cache
        with open(self.terrain_string_pickle_path, 'wb') as handle:
            pickle.dump(self.terrain_string_cache, handle, protocol=pickle.HIGHEST_PROTOCOL)


# networkx graph of world
class World:

    def __init__(self, config_file_location):

        # connect to api
        self.api = create_api_connection_from_config(config_file_location)

        # read world configuration parameters
        config = configparser.ConfigParser()
        config.read(config_file_location)

        # world data (W60N60 to E60S60 for shard3)
        self.bottom_left_room_js_row_col = room_js_row_col(config['WORLD']['bottom_left_room'].strip())
        self.top_right_room_js_row_col = room_js_row_col(config['WORLD']['top_right_room'].strip())

        # terrain
        self.terrain = Terrain(api=self.api, bottom_left_room_js_row_col=self.bottom_left_room_js_row_col,
                               top_right_room_js_row_col=self.top_right_room_js_row_col)

        # objects
        self.game_objects = {}
        self.tasks = {}

    def get_snapshot(self):
        self.game_objects = {}
        for player in self.players:
            self.game_objects.update(player.get_snapshot())

    def point_from_js_pos(self, snapshot_json):
        return Room(room_name=snapshot_json['room_name'], bottom_left_js_row_col=self.bottom_left_room_js_row_col).point_from_js_pos(snapshot_json)

    def room_from_point(self, point):
        room_col = int(point.x/50)
        room_row = int(point.y/50)
        return Room(row=room_row, col=room_col, bottom_left_js_row_col=self.bottom_left_room_js_row_col)

    def init_new_turn(self):
        self.game_objects = {}
        self.tasks = {}



