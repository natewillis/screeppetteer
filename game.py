import screepsapi
import logging
import configparser
import sched, time
from GameObjects import Creep, Source, Spawn, Flag

class Game:

    def __init__(self):

        # get username and password from safe file
        config = configparser.ConfigParser()
        config.read('screepy.config')

        # assign arguments
        self.user = config['DEFAULT']['user']
        self.password = config['DEFAULT']['password']
        self.host = config['DEFAULT']['password'] if 'host' in config['DEFAULT'] else None
        self.seconds_per_cycle = config['DEFAULT']['seconds_per_cycle']
        self.frozen_ticks = config['DEFAULT']['frozen_ticks']
        self.future_ticks = config['DEFAULT']['future_ticks']
        self.shard = 'shard3'  # hardcode for now, probably put in config but need to see how localhost works

        # init connection to screeps api
        self.api = None
        self.connect()

        # init game map (whole thing?)
        #self.terrain_map = Map();

        # init game objects
        self.snapshot_tick = 0
        self.__game_objects = {}
        self.tasks = {}
        self.unknown_id_count = 0

        # setup logging
        logging.basicConfig(filename='./logs/screepy.log', format='%(asctime)s\(%(levelname)s\): %(message)s',
                            level=logging.DEBUG)

        # setup scheduler if we wanted to run jobs perioidically
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

    @property
    def game_objects(self):
        return self.__game_objects

    @game_objects.setter
    def game_objects(self, game_objects):
        self.__game_objects = game_objects

    def empire_objects(self, empire_flag_name):
        #TODO: filter out empire objects for a given flag
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
        self.tasks = [tick: task for (tick, task) in raw_memory['tasks'].items() if
                      int(tick) < (self.snapshot_tick + self.frozen_ticks)]

    def execute_cycle(self):

        # get snapshot

        self.get_snapshot();

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

            #if container_on_closest_source:
            #    energy_game_state = 1

            # Job requirements

            #if energy_game_state == 0:

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