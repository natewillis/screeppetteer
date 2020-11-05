import networkx as nx
import configparser
from screeps_utilities import js_row_col_to_room, create_api_connection_from_config, js_room_row_col
import os
import numpy as np
import pickle
import constants

# logging
import logging
logger = logging.getLogger(__name__)


class Point:

    def __init__(self, x=0, y=0, snapshot_json=None, world=None):

        # bottom left js row col for room operations
        self.world = world

        # create point from either snapshot or directly
        if snapshot_json is None:
            self.x = x
            self.y = y
        else:
            point = Room(room_name=snapshot_json['room_name'], world=self.world).point_from_js_pos(snapshot_json)
            self.x = point.x
            self.y = point.y

    def __str__(self):
        return f'x:{self.x} y:{self.y}'

    def __hash__(self):
        return self.x, self.y

    def range(self, point):
        return max((self.x-point.x)(self.y-point.y))

    @property
    def room(self):
        room_col = int(self.x / 50)
        room_row = int(self.y / 50)
        return Room(row=room_row, col=room_col, world=self.world)

    @property
    def js_x_y(self):

        # get room
        room = self.room

        # get relative x y centered at bottom left
        x = self.x - room.bottom_left_point.x
        y = self.y - room.bottom_left_point.y

        # get flipped y
        local_y = 50 - (y + 1)

        return {'x': x, 'y': local_y}

    @property
    def js_x(self):
        return self.js_x_y['x']

    @property
    def js_y(self):
        return self.js_x_y['y']

    def path_to(self, to_point, bad_pts=[], include_static_objects=True, ignore_terrain_differences=False):
        return self.world.path_between(from_point=self, to_point=self, bad_pts=bad_pts, include_static_objects=include_static_objects, ignore_terrain_differences=ignore_terrain_differences)

    @property
    def node(self):
        return self.x, self.y

    @property
    def edge_type(self):
        js_x_y = self.js_x_y
        if js_x_y['x'] == 0:
            return 'W'
        elif js_x_y['x'] == 49:
            return 'E'
        elif js_x_y['y'] == 0:
            return 'N'
        elif js_x_y['y'] == 49:
            return 'S'
        else:
            return None

    @property
    def terrain(self):
        return self.world.terrain.terrain_matrix[self.y, self.x]

    def move_direction_to_point(self, to_point):

        # calculate delta
        d_x = to_point.x - self.x
        d_y = to_point.y - self.y

        if d_x == 0 and d_y == 0:
            return None
        elif d_x == 0 and d_y == 1:
            return constants.TOP
        elif d_x == 0 and d_y == -1:
            return constants.BOTTOM
        elif d_x == -1 and d_y == 0:
            return constants.LEFT
        elif d_x == -1 and d_y == 1:
            return constants.TOP_LEFT
        elif d_x == -1 and d_y == -1:
            return constants.BOTTOM_LEFT
        elif d_x == 1 and d_y == 0:
            return constants.RIGHT
        elif d_x == 1 and d_y == 1:
            return constants.TOP_RIGHT
        elif d_x == 1 and d_y == -1:
            return constants.BOTTOM_RIGHT
        else:
            print(f'{self} to {to_point} is dx{d_x} and dy{d_y}')
            return None


class Room:

    def __init__(self, row=0, col=0, room_name=None, world=None):

        # init properties
        self.__row = row
        self.__col = col

        # top left row col
        self.__bottom_left_js_col = 0
        self.__bottom_left_js_row = 0
        if world is not None:
            self.world = world
            self.__bottom_left_js_row = self.world.bottom_left_room_js_row_col['row']
            self.__bottom_left_js_col = self.world.bottom_left_room_js_row_col['col']

        # convert room_name
        if room_name is not None:
            row_col = js_room_row_col(room_name)
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
        return Point(x=self.col * 50, y=self.row * 50)

    def point_from_terrain_index(self, terrain_index):

        # calculate row from the top
        local_y_from_top = (terrain_index // 50)
        local_y = 50 - (local_y_from_top + 1)
        local_x = (terrain_index - (local_y_from_top * 50))

        # absolute position
        y = local_y + (self.row * 50)
        x = local_x + (self.col * 50)

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
        y = local_y + (self.row * 50)
        x = local_x + (self.col * 50)

        # return point object
        return Point(x=x, y=y)


class Line:

    def __init__(self, points=None):
        if points is None:
            self.points == []
        else:
            self.points = points


class Terrain:
    def __init__(self, api, world, shard='shard3'):

        # world info
        self.world = world
        self.bottom_left_room_js_row_col = self.world.bottom_left_room_js_row_col
        self.top_right_room_js_row_col = self.world.top_right_room_js_row_col
        self.shard = shard

        # terrain cache data
        self.terrain_matrix = None
        self.terrain_pickle_path = 'data/terrain_cache.pickle'
        self.terrain_cache = {}
        if os.path.exists(self.terrain_pickle_path):
            with open(self.terrain_pickle_path, 'rb') as handle:
                self.terrain_cache = pickle.load(handle)
                if self.world.host_pickle_key in self.terrain_cache:
                    self.terrain_matrix = self.terrain_cache[self.world.host_pickle_key][self.shard]

        # only update the matrix if needed
        if self.terrain_matrix is None:

            # connection
            logger.info(f'terrain was sent api with host {api.host} and token {api.token}')
            self.api = api

            # terrain string cache data
            self.terrain_string_cache = {}
            self.terrain_string_pickle_path = 'data/terrain_string_cache.pickle'
            if os.path.exists(self.terrain_string_pickle_path):
                with open(self.terrain_string_pickle_path, 'rb') as handle:
                    self.terrain_string_cache = pickle.load(handle)

            # load terrain
            self.init_terrain_map()

    def update_terrain_map_from_room(self, room):

        # pull terrain string from cache or room
        terrain_string = ''
        if self.world.host_pickle_key in self.terrain_string_cache:
            if self.shard in self.terrain_string_cache:
                if room.js_room_name in self.terrain_string_cache:
                    terrain_string = self.terrain_string_cache[self.world.host_pickle_key][self.shard][room.js_room_name]
                    logger.info(f'pulled {room.js_room_name} from cache')

        # retrieve it since we couldn't get it from cache
        if terrain_string == '':
            # get terrain string from server
            terrain_string_req_return = self.api.room_terrain(room=room.js_room_name, shard=self.shard, encoded=True)
            terrain_string = terrain_string_req_return['terrain'][0]['terrain']

            # build terrain string cache keys if necessary
            if self.world.host_pickle_key not in self.terrain_string_cache:
                self.terrain_string_cache[self.world.host_pickle_key] = {}
            if self.shard not in self.terrain_string_cache[self.world.host_pickle_key]:
                self.terrain_string_cache[self.world.host_pickle_key][self.shard] = {}

            # store the terrain string in the cache
            self.terrain_string_cache[self.world.host_pickle_key][self.shard][room.js_room_name] = terrain_string

            # logging
            logger.info(f'pulled {room.js_room_name} from server')

        # loop through terrain string for weights
        for terrain_character_index in range(0, len(terrain_string)):
            terrain_point = room.point_from_terrain_index(terrain_character_index)
            terrain_character = terrain_string[terrain_character_index]
            terrain_weight = 255  # wall
            if terrain_character == '0':  # plain
                terrain_weight = 2
            elif terrain_character == '2':  # swamp
                terrain_weight = 10
            if terrain_point.edge_type is not None:
                terrain_weight += .4
            self.terrain_matrix[terrain_point.y, terrain_point.x] = terrain_weight

    def init_terrain_map(self):

        # define rows
        world_rows = abs(self.bottom_left_room_js_row_col['row'] - self.top_right_room_js_row_col['row']) + 1
        world_cols = abs(self.bottom_left_room_js_row_col['col'] - self.top_right_room_js_row_col['col']) + 1

        # init numpy array
        logger.info(f'world has rows {world_rows} and cols {world_cols}')
        self.terrain_matrix = np.zeros((world_rows * 50, world_cols * 50))

        # loop through rows
        for world_row in range(0, world_rows):
            for world_col in range(0, world_cols):
                world_room = Room(row=world_row, col=world_col, world=self.world)
                self.update_terrain_map_from_room(world_room)

        # save cache
        with open(self.terrain_string_pickle_path, 'wb') as handle:
            pickle.dump(self.terrain_string_cache, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open(self.terrain_pickle_path, 'wb') as handle:
            if self.world.host_pickle_key not in self.terrain_cache:
                self.terrain_cache[self.world.host_pickle_key] = {}
            self.terrain_cache[self.world.host_pickle_key][self.shard] = self.terrain_matrix
            pickle.dump(self.terrain_cache, handle, protocol=pickle.HIGHEST_PROTOCOL)


# networkx graph of world
class World:

    def __init__(self, config_file_location):

        # read world configuration parameters
        config = configparser.ConfigParser()
        config.read(config_file_location)

        # check if this is a test run
        self.test = False
        if 'TEST' in config:
            if 'no_server_test' in config['TEST']:
                self.test = config['TEST']['no_server_test']

        # connect to api
        self.api = None
        if not self.test:
            self.api = create_api_connection_from_config(config_file_location)

        # pickle keys
        if self.test:
            self.host_pickle_key = 'local'
        else:
            self.host_pickle_key = 'public' if self.api.host is None else 'local'

        # world data (W60N60 to E60S60 for shard3)
        self.bottom_left_room_js_row_col = js_room_row_col(config['WORLD']['bottom_left_room'].strip())
        self.top_right_room_js_row_col = js_room_row_col(config['WORLD']['top_right_room'].strip())

        # terrain
        self.terrain = Terrain(api=self.api, world=self)

        # cache networkx grid
        self.networkx_graph = None
        self.networkx_graph_pickle_path = 'data/networkx_graph.pickle'
        if os.path.exists(self.networkx_graph_pickle_path):
            with open(self.networkx_graph_pickle_path, 'rb') as handle:
                self.networkx_graph = pickle.load(handle)

        # networkx grid
        self.init_networkx_graph()

        # objects
        self.game_objects = {}

    def get_snapshot(self):
        self.game_objects = {}
        for player in self.players:
            self.game_objects.update(player.get_snapshot())

    def point(self, x=0, y=0, snapshot_json=None):
        return Point(x=x, y=y, snapshot_json=snapshot_json, world=self)

    def init_new_turn(self):
        self.game_objects = {}

    def init_networkx_graph(self):

        if self.networkx_graph is None:

            # init empty graph
            self.networkx_graph = nx.Graph()

            # parameters for easy calcs
            num_rows, num_cols = self.terrain.terrain_matrix.shape
            max_x = num_cols - 1
            max_y = num_rows - 1

            # create a point for each location on map
            print('init networkx graph')
            for x in range(0, num_cols):
                for y in range(0, num_rows):
                    start_point = Point(x=x, y=y, world=self)
                    for d_x in [-1, 0, 1]:
                        for d_y in [-1, 0, 1]:

                            # don't worry about the center point
                            if d_x == 0 and d_y == 0:
                                continue

                            # create end node
                            end_x = x + d_x
                            end_y = y + d_y

                            # create end node
                            end_point = Point(x=end_x, y=end_y, world=self)

                            # test if this point is valid
                            if end_point.x > max_x or end_point.x < 0:
                                continue
                            if end_point.y > max_y or end_point.y < 0:
                                continue

                            # linkage logic for exit tiles
                            if start_point.edge_type == 'N' and end_point.edge_type is not None and d_x != 0:
                                continue
                            if start_point.edge_type == 'S' and end_point.edge_type is not None and d_x != 0:
                                continue
                            if start_point.edge_type == 'E' and end_point.edge_type is not None and d_y != 0:
                                continue
                            if start_point.edge_type == 'W' and end_point.edge_type is not None and d_y != 0:
                                continue

                            # add edges
                            self.networkx_graph.add_nodes_from([start_point.node, end_point.node])
                            self.networkx_graph.add_edge(start_point.node, end_point.node)

            # save the graph
            with open(self.networkx_graph_pickle_path, 'wb') as handle:
                pickle.dump(self.networkx_graph, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def path_between(self, from_point, to_point, bad_pts=[], include_static_objects=True, ignore_terrain_differences=False):

        # find path with just terrain
        start_grid = self.terrain.terrain_matrix.copy()

        # terrain ignorance (for roads and the like)
        if ignore_terrain_differences:
            start_grid[start_grid == 10] = 2
            start_grid[start_grid == 1] = 2

        # static object pts
        if include_static_objects:
            for game_object in self.game_objects.values():
                if game_object.static_object:
                    if not game_object.passable:
                        pt = game_object.starting_location
                        start_grid[pt.y, pt.x] = 255

        # dynamic points to remove
        for pt in bad_pts:
            start_grid[pt.y, pt.x] = 255

        # define weight function
        def weight_func(from_tuple, to_tuple, edge_dictionary):
            return start_grid[from_tuple[1], from_tuple[0]]

        path = nx.astar_path(G=self.networkx_graph, source=from_point.node, target=to_point.node, weight=weight_func)
        return path

    def path_for_body_at_time(self, from_point, to_point, start_tick, body, start_fatigue=0):

        # get start path
        start_path = self.path_between(from_point, to_point)
        actual_path = [from_point]
        actual_path_ticks = [start_tick]
        bad_pts = []
        current_index = 1
        current_tick = start_tick
        current_move_from_point = self.point(x=start_path[current_index-1][1], y=start_path[current_index-1][0])
        current_move_to_point = self.point(x=start_path[current_index][1], y=start_path[current_index][0])

        # loop through each point
        while current_move_from_point.node != to_point.node:

            # deal with fatigue calcs
            while start_fatigue > 0:
                current_tick += 1
                start_fatigue -= min(body.count('move') * 2, start_fatigue)

            # search for obstacles in the next spot to move
            has_obstacle = False
            for game_object in self.game_objects:
                if not game_object.static_object:
                    if not game_object.passable:
                        if game_object.location(current_tick+1).node == current_move_to_point.node:
                            has_obstacle = True

            # we can move!
            if not has_obstacle:
                actual_path.append(current_move_to_point)
                actual_path_ticks.append(current_tick)
                current_index += 1
                current_move_from_point = self.point(x=start_path[current_index - 1][1], y=start_path[current_index - 1][0])
                current_move_to_point = self.point(x=start_path[current_index][1], y=start_path[current_index][0])
                start_fatigue += int(current_move_to_point.terrain)*len(body)
                bad_pts = []
            # something is in our way, replan!
            else:
                bad_pts.append(current_move_to_point)
                start_path = self.path_between(current_move_from_point, to_point, off_limit_pts=bad_pts)
                current_index = 1
                current_move_from_point = self.point(x=start_path[current_index - 1][1], y=start_path[current_index - 1][0])
                current_move_to_point = self.point(x=start_path[current_index][1], y=start_path[current_index][0])

        # we made it through!
        print(f'path {actual_path} which took {current_tick - start_tick} ticks to travel {len(actual_path)}')
        return actual_path, actual_path_ticks










