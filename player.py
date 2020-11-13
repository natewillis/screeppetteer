from screeps_utilities import create_api_connection_from_config
import configparser
from game_objects import Spawn, Flag, Source, Creep, Controller
import constants

# logging
import logging

logger = logging.getLogger(__name__)


class Player:
    def __init__(self, config_file_location, world, director):

        # assign director
        self.director = director

        # get username and password from safe file
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

        # store a reference to the world the player is in
        self.world = world

        # player info
        self.shard = config['WORLD']['shard']
        self.player_name = config['PLAYER']['player_name']

        # init objects
        self.tasks = {}

        # init timing
        self.snapshot_tick = 0

    def get_snapshot(self, saved_snapshot=None):

        # query screeps for snapshot memory
        if saved_snapshot is None:
            raw_memory_response = self.api.memory('', shard=self.shard)  # assuming json dictionary at this point
            raw_memory = raw_memory_response['data']
        else:
            raw_memory = saved_snapshot
        logger.info(raw_memory_response)

        # grab the current tick
        self.snapshot_tick = int(raw_memory['snapshot']['game_time'])

        # init game objects
        game_objects = {}

        # process snapshot objects
        for game_object_id, game_object in raw_memory['snapshot']['objects'].items():
            if game_object['code_type'] == 'structure':
                if game_object['structure_type'] == 'spawn':
                    game_objects[game_object['universal_id']] = Spawn(game_object_json=game_object,
                                                                      tick=self.snapshot_tick, world=self.world,
                                                                      player=self)
                elif game_object['structure_type'] == 'controller':
                    game_objects[game_object['universal_id']] = Controller(game_object_json=game_object,
                                                                           tick=self.snapshot_tick, world=self.world,
                                                                           player=self)
            elif game_object['code_type'] == 'flag':
                game_object['owner'] = self.player_name
                game_objects[game_object['universal_id']] = Flag(game_object_json=game_object, tick=self.snapshot_tick,
                                                                 world=self.world, player=self)
            elif game_object['code_type'] == 'source':
                game_objects[game_object['universal_id']] = Source(game_object_json=game_object,
                                                                   tick=self.snapshot_tick, world=self.world,
                                                                   player=self)
            elif game_object['code_type'] == 'creep':
                game_objects[game_object['universal_id']] = Creep(game_object_json=game_object, tick=self.snapshot_tick,
                                                                  world=self.world, player=self)

        # update world objects
        self.world.game_objects.update(game_objects)

        # grab existing tasks
        self.tasks = raw_memory['tasks']

    def commit_tasks(self):
        logger.info(f'commiting tasks {self.tasks}')
        self.api.set_memory('tasks', self.tasks)

    @property
    def kingdom_flags(self):
        return [flag for flag in self.world.game_objects.values() if
                flag.specific_type == 'flag' and flag.color == constants.COLOR_RED and flag.owner == self.player_name]

    def my_creeps(self, tick, kingdom_flag=None):
        if kingdom_flag is None:
            return [creep for creep in self.world.game_objects if
                    creep.specific_type == 'creep' and
                    creep.owner == self.player_name and
                    creep.alive(tick)]
        else:
            return [creep for creep in self.director.kingdom_game_objects(kingdom_flag) if
                    creep.specific_type == 'creep' and
                    creep.owner == self.player_name and
                    creep.alive(tick)]
