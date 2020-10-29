from screeps_utilities import create_api_connection_from_config
import configparser
from game_objects import Spawn, Flag, Source, Creep

# logging
import logging
logger = logging.getLogger(__name__)


class Player:
    def __init__(self, config_file_location, world):

        # connect to api
        self.api = create_api_connection_from_config(config_file_location)

        # store a reference to the world the player is in
        self.world = world

        # get username and password from safe file
        config = configparser.ConfigParser()
        config.read(config_file_location)

        # player info
        self.shard = config['WORLD']['shard']
        self.player_name = config['PLAYER']['player_name']

        # init objects
        self.game_objects = {}
        self.tasks = {}

        # init timing
        self.snapshot_tick = 0

    def get_snapshot(self):

        # query screeps for snapshot memory
        raw_memory_response = self.api.memory('', shard=self.shard)  # assuming json dictionary at this point
        raw_memory = raw_memory_response['data']
        print(raw_memory_response)

        # grab the current tick
        self.snapshot_tick = int(raw_memory['snapshot']['game_time'])

        # clear out game objects
        self.game_objects = {}

        # process snapshot objects
        for game_object_id, game_object in raw_memory['snapshot']['objects'].items():
            if game_object['code_type'] == 'structure':
                if game_object['structure_type'] == 'spawn':
                    self.game_objects[game_object['name']] = Spawn(game_object_json=game_object,
                                                                   tick=self.snapshot_tick, world=self.world)
            elif game_object['code_type'] == 'flag':
                self.game_objects[game_object['name']] = Flag(game_object_json=game_object, tick=self.snapshot_tick, world=self.world)
            elif game_object['code_type'] == 'source':
                self.game_objects[game_object['id']] = Source(game_object_json=game_object, tick=self.snapshot_tick, world=self.world)
            elif game_object['code_type'] == 'creep':
                self.game_objects[game_object['name']] = Creep(game_object_json=game_object, tick=self.snapshot_tick, world=self.world)

        # update world objects
        self.world.game_objects.update(self.game_objects)

        # grab existing tasks
        self.tasks = raw_memory['tasks']

    def commit_tasks(self):
        self.api.set_memory('tasks', self.tasks)

