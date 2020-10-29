import screepsapi
import configparser
import sched
import time
import pickle
import os
import numpy as np
from game_objects import Creep, Source, Spawn, Flag
from screeps_utilities import room_js_row_col
import logging
logger = logging.getLogger(__name__)

class Game:

    def __init__(self):

        # setup logging
        logging.basicConfig(filename='./logs/screepy.log', format='%(asctime)s\(%(levelname)s\): %(message)s',
                            level=logging.DEBUG)

        # get username and password from safe file
        config = configparser.ConfigParser()
        config.read('screepy.config')

        # server data
        self.user = config['DEFAULT']['user']
        self.password = config['DEFAULT']['password']
        self.host = config['DEFAULT']['host'] if 'host' in config['DEFAULT'] else None
        self.host_string = self.host if self.host is not None else 'public'
        self.shard = config['DEFAULT']['shard']

        # program constraints
        self.seconds_per_cycle = config['DEFAULT']['seconds_per_cycle']
        self.frozen_ticks = config['DEFAULT']['frozen_ticks']
        self.future_ticks = config['DEFAULT']['future_ticks']

        # world data (W60N60 to E60S60 for shard3)
        self.top_left_room_js_row_col = room_js_row_col(config['DEFAULT']['top_left_room'].strip())
        self.bottom_right_room_js_row_col = room_js_row_col(config['DEFAULT']['bottom_right_room'].strip())

        # init connection to screeps api
        self.api = None
        self.connect()

        # terrain
        self.terrain_string_cache = {}
        self.terrain_string_pickle_path = 'data/terrain_string_cache.pickle'
        if os.path.exists(self.terrain_string_pickle_path):
            with open(self.terrain_string_pickle_path, 'rb') as handle:
                self.terrain_string_cache = pickle.load(handle)
        self.init_terrain_map()

        # init game objects
        self.snapshot_tick = 0
        self.__game_objects = {}
        self.tasks = {}
        self.unknown_id_count = 0

        self.terrain = None

        # setup scheduler if we wanted to run jobs periodically
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def connect(self):

        # test if we have a valid connection
        if self.api is not None:
            pass

        # connect if needed
        if self.api is None:
            if self.host is None:
                logging.info(f'no host was provided so connecting to main servers as {self.user}')
                self.api = screepsapi.API(u=self.user, p=self.password)
            else:
                logging.info(f'connecting to {self.host} as {self.user}')
                self.api = screepsapi.API(u=self.user, p=self.password, host=self.host)

    def room(self, *args, **kwargs):

        # manipulate kwargs
        kwargs['top_left_js_row_col'] = self.top_left_room_js_row_col

        # get fill in game data for this room
        return Room(*args, **kwargs)

    def update_terrain_map_from_room(self, room):

        # pull terrain string from cache or room
        terrain_string = ''

        if self.host_string in self.terrain_string_cache:
            if self.shard in self.terrain_string_cache:
                if room.js_room_name in self.terrain_string_cache:
                    terrain_string = self.terrain_string_cache[self.host_string][self.shard][room.js_room_name]
                    logging.info(f'pulled {room.js_room_name} from cache')

        # retrieve it since we couldn't get it from cache
        if terrain_string == '':
            # get terrain string from server
            terrain_string_req_return = self.api.room_terrain(room=room.js_room_name, shard=self.shard, encoded=True)
            terrain_string = terrain_string_req_return['terrain'][0]['terrain']
            self.terrain_string_cache[self.host_string][self.shard][room.js_room_name] = terrain_string
            logging.info(f'pulled {room.js_room_name} from server')

        # loop through terrain string for weights
        for terrain_character_index in range(0, len(terrain_string) ):
            terrain_point = room.point_from_terrain_index(terrain_character_index)
            terrain_character = terrain_string[terrain_character_index]
            terrain_weight = 255  # wall
            if terrain_character == '0':  # plain
                terrain_weight = 2
            elif terrain_character == '1': # swamp
                terrain_weight = 10
            self.terrain[terrain_point.y, terrain_point.x] = terrain_weight

    def init_terrain_map(self):

        # define rows
        world_rows = abs(self.top_left_room_js_row_col['row'] - self.bottom_right_room_js_row_col['row']) + 1
        world_cols = abs(self.top_left_room_js_row_col['col'] - self.bottom_right_room_js_row_col['col']) + 1

        # init numpy array
        self.terrain = np.zeros((world_rows * 50, world_cols * 50), dtype=np.intc)

        # loop through rows
        for world_row in range(0, world_rows):
            for world_col in range(0, world_cols):
                world_room = self.room(row=world_row, col=world_col)
                self.update_terrain_map_from_room(world_room)

        # save cache
        with open(self.terrain_string_pickle_path, 'wb') as handle:
            pickle.dump(self.terrain_string_cache, handle, protocol=pickle.HIGHEST_PROTOCOL)

        print(self.terrain)

    @property
    def game_objects(self):
        return self.__game_objects

    @game_objects.setter
    def game_objects(self, game_objects):
        self.__game_objects = game_objects

    def empire_objects(self, empire_flag_name):
        # TODO: filter out empire objects for a given flag
        return self.__game_objects

    def filter_structures(self, structure_type='all'):

        # init return_array
        return_array = []

        # loop through objects and filter if criteria are met
        for game_object in self.game_objects.items():
            if game_object.code_type == 'structure':
                if structure_type == 'all':
                    return_array.append(game_object)
                else:
                    if game_object.structure_type == structure_type:
                        return_array.append(game_object)

    def filter_objects(self, code_type='all'):

        # init return_array
        return_array = []

        # loop through objects and filter if criteria are met
        for game_object in self.game_objects.items():
            if code_type == 'all':
                return_array.append(game_object)
            else:
                if game_object.code_type == code_type:
                    return_array.append(game_object)

    def update_objects(self):
        # check to make sure that any newly spawned objects due to spawn tasks have been added to self.objects
        pass

    def get_snapshot(self):

        # query screeps for snapshot memory
        raw_memory = self.api.memory('', shard=self.shard)  # assuming json dictionary at this point
        print(raw_memory)

        # grab the current tick
        self.snapshot_tick = int(raw_memory['snapshot']['game_time'])

        # clear out game objects
        self.game_objects = {}

        # process snapshot objects
        for game_object in raw_memory['snapshot']['objects']:
            if game_object['code_type'] == 'creep':
                self.game_objects[game_object.name] = Creep(snapshot_json=game_object, tick=self.snapshot_tick)
            elif game_object['code_type'] == 'source':
                self.game_objects[game_object.id] = Source(snapshot_json=game_object, tick=self.snapshot_tick)
            elif object['code_type'] == 'structure':
                if object['structure_type'] == 'spawn':
                    self.objects[game_object.name] = Spawn(snapshot_json=game_object, tick=self.snapshot_tick)

        # initalize new tasks (the tasks are what tells us that a firm decision has been made for the creeps activity)
        # the tasks are what will tell us if a creep is already filling a job
        #TODO: filter tasks down to the ones from snapshot time to frozen ticks

    def execute_cycle(self):

        # get snapshot
        self.get_snapshot()

        # process jobs (once the creep has a task assigned, it cant be changed)
        # tasks are the criteria that determine if a job has been filled)
        # need to account for uncreated objects so far
        # TODO: Enemy SA

        # Resource Extraction
        self.update_objects()  # creates new objects if needed due to spawn

        # setup loop
        tick = self.snapshot_tick + self.frozen_ticks
        last_tick = self.snapshot_tick + self.future_ticks

        while tick <= last_tick:
            # Detect game state
            # Level 0: Manual Energy Harvest
            energy_game_state = 0  # init at lowest level
            # Level 1: Harvest Pod Staffing
            containers = self.filter_structures('container')
            sources = self.filter_structures('source')

            # Code to see if theres a container on the closest source
            # if container_on_closest_source:
            #    energy_game_state = 1
            # Job requirements
            # if energy_game_state == 0:

        # Check if the creep who did the task last time was still around, if so use him
        # If he's not there or there wasn't one last time or there wasnt a task for some reason, find the nearest utility creep [WORK,CARRY,MOVE,MOVE]
        # If neither of those are possible, check if
        # Condition 1:
        # - Find the closest not full one
        # - If its on the energy source, let it harvest

        # Utility Planning

        # Transport Planning

        # Tactical Planning

        # Surge Planning

    def execute_cycle_with_scheduler(self, next_start_time):

        # run cycle
        self.execute_cycle()

        # increment next_start_time
        next_start_time = round(next_start_time + self.seconds_per_cycle, 0)

        # schedule the next go around
        self.scheduler.enterabs(next_start_time, 1, self.execute_cycle_with_scheduler, argument=(next_start_time,))

    def execute_cycles_forever(self):

        # calculate the first cycle UTC time (start on a number of seconds divisible by 10)
        next_start_time = round(time.time() + self.seconds_per_cycle, -1)

        # start first task
        self.scheduler.enterabs(next_start_time, 1, self.execute_cycle_with_sched, argument=(next_start_time,))
        logging.info(f'starting scheduler at {time.time()}')
        self.scheduler.run()
