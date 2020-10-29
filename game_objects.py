import uuid
from world import Point
import constants

# logging
import logging
logger = logging.getLogger(__name__)


# classes
class GameObject:

    def __init__(self, game_object_json, tick, world):

        # world reference
        self.world = world

        # static parameters
        self.js_id = game_object_json['id'] if 'id' in game_object_json else None
        self.name = game_object_json['name'] if 'name' in game_object_json else None
        self.code_type = game_object_json['code_type'] if 'code_type' in game_object_json else None
        self.structure_type = game_object_json['structure_type'] if 'structure_type' in game_object_json else None
        self.hits_max = game_object_json['hits_max'] if 'hits_max' in game_object_json else None
        self.color = game_object_json['color'] if 'color' in game_object_json else None
        self.secondary_color = game_object_json['secondary_color'] if 'secondary_color' in game_object_json else None
        self.owner = game_object_json['owner'] if 'owner' in game_object_json else None

        # special parameters
        self.__store = Store(game_object_json=game_object_json['store'], tick=tick) if 'store' in game_object_json else None


        # specific type is the combo of structure type and code_type
        self.specific_type = ''
        if self.structure_type is None:
            self.specific_type = self.code_type
        else:
            self.specific_type = self.structure_type

        # dynamic parameters
        #TODO: get initial location converted
        self.__initial_location = Point(snapshot_json=game_object_json['pos'], world=self.world)
        self.__initial_tick = tick
        self.__current_tick = self.__initial_tick
        self.__initial_hits = game_object_json['hits'] if 'hits' in game_object_json else None
        self.__current_hits = self.__initial_hits

    def reset_properties(self):
        self.__current_tick = self.__initial_tick

    def propagate_to_tick(self, tick):
        while self.__current_tick < tick:
            self.__current_tick += 1

    def js_id(self):
        return self.type

    def location(self, tick):
        return self.__initial_location

    @property
    def starting_location(self):
        return self.location(self.snapshot_tick)

    def nice_id(self):
        if self.name is None:
            return self.name
        else:
            return self.js_id

    def __str__(self):
        return f'{self.specific_type} with id of {self.nice_id()} initialized at tick {self.__initial_tick}'

    @property
    def snapshot_tick(self):
        return self.__initial_tick


class MovingObject(GameObject):
    pass


class Creep(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)


class Store:

    def __init__(self, game_object_json, tick):
        self.__initial_capacity = game_object_json['capacity'].copy()
        self.__initial_used_capacity = game_object_json['used_capacity']

        # initial parameters
        self.__initial_tick = tick

        # dynamic parameters
        self.__current_tick = tick
        self.__current_capacity = self.__initial_capacity.copy()

    def __str__(self):
        return f'source with contents {self.__current_capacity.items()}'


class Spawn(GameObject):

    def __init__(self, *args, **kwargs):

        # run parent init
        GameObject.__init__(self, *args, **kwargs)

    def __str__(self):
        return f'spawn named {self.nice_id()} and store {self._GameObject__store}'


class Flag(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)


class Source(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
