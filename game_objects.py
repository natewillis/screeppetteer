import uuid
from world import Point
import constants
from screeps_utilities import creep_body_resource_cost, delta_from_direction

# logging
import logging

logger = logging.getLogger(__name__)


# classes
class GameObject:

    def __init__(self, game_object_json, tick, world, player=None):

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
        self.player = player
        self.detailed_body = game_object_json['detailed_body'] if 'detailed_body' in game_object_json else None
        self.static_object = True
        self.passable = False

        # special parameters
        self.store = Store(game_object_json=game_object_json['store'],
                           tick=tick, world=world) if 'store' in game_object_json else None

        # specific type is the combo of structure type and code_type
        self.specific_type = ''
        if self.structure_type is None:
            self.specific_type = self.code_type
        else:
            self.specific_type = self.structure_type

        # dynamic parameters
        # TODO: get initial location converted
        self.__initial_location = Point(snapshot_json=game_object_json['pos'], world=self.world)
        self.__initial_tick = tick
        self.__initial_hits = game_object_json['hits'] if 'hits' in game_object_json else None

    @property
    def tasks(self):

        # init tasks
        tasks = {}

        # only owned objects can be busy with tasks
        if self.owner is None:
            return tasks

        # get player task queue
        player_tasks = self.player.tasks

        # get all my tasks out
        for tick in player_tasks:
            if self.universal_id in player_tasks[tick]:
                tasks[tick] = player_tasks[tick][self.universal_id]

        # return tasks
        return tasks

    def add_task(self, task):
        if task.tick not in self.player.tasks:
            self.player.tasks[task.tick] = {}
        self.player.tasks[task.tick][self.universal_id] = task

    def reset_properties(self):
        pass

    def location(self, tick):
        return self.__initial_location

    @property
    def starting_location(self):
        return self.__initial_location

    def __str__(self):
        return f'{self.specific_type} with id of {self.universal_id} initialized at tick {self.__initial_tick}'

    @property
    def snapshot_tick(self):
        return self.__initial_tick

    def __hash__(self):
        if self.code_type == 'structure':
            return hash((self.structure_type, self.starting_location.x, self.starting_location.y))
        elif self.code_type == 'source':
            return hash(self.js_id)
        elif self.code_type == 'creep':
            return hash(self.name)
        elif self.code_type == 'flag':
            return hash(self.name)

    @property
    def universal_id(self):
        if self.code_type == 'structure':
            return f'{self.structure_type}-{self.starting_location.room.js_room_name}-{self.starting_location.room_x}-{self.starting_location.room_y}'
        elif self.code_type == 'source':
            return f'{self.js_id}'
        elif self.code_type == 'creep':
            return f'{self.name}'
        elif self.code_type == 'flag':
            return f'{self.name}'

    def busy(self, tick, number_of_ticks=1):

        # init return
        busy = False

        # only owned objects can be busy with tasks
        if self.owner is None:
            return False

        # get task queue
        tasks = self.tasks

        # loop through period to see if tasks
        for tick in range(tick, tick + number_of_ticks):
            if tick in tasks:
                busy = True

        # return busy
        return busy

    @property
    def kingdom_flag(self):

        # only players have kingdom flags
        if self.player is None:
            return None

        # find closest flag
        return min(self.player.kingdom_flags, key=lambda flag: self.starting_location.range(flag.starting_location))


class Creep(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
        self.static_object = False

    def location(self, tick):

        # make sure theyre not asking for something unreasonable
        if tick < self.snapshot_tick:
            return None

        # get tasks
        tasks = self.tasks

        # init location
        current_location = self.starting_location
        for current_tick in range(self.snapshot_tick, tick - 1):
            if current_tick in tasks:
                task = tasks[current_tick]
                if task['type'] == 'move':
                    direction = task['details']['direction']
                    delta = delta_from_direction(direction)
                    current_location = Point(x=(current_location.x + delta['x']), y=(current_location.y + delta['y']),
                                             world=self.world)

        # return propagated locaiton
        return current_location

    @property
    def body(self):
        body = []
        # TODO: account for hits and boost
        for body_detail in self.detailed_body:
            body.append(body_detail['type'])
        return body

    def assign_path(self, path, start_tick):
        if len(path) <= 1:
            return False
        for pt_num in range(1, len(path)):
            # create move task
            task = {
                'received': False,
                'tick': start_tick,
                'assigned_to': self.universal_id,
                'type': 'move',
                'desired_return_value': 0,
                'details': {
                    'direction': path[pt_num-1].move_direction_to_point(path[pt_num]),
                }
            }
            self.add_task(task)
        return True


class Store:

    def __init__(self, game_object_json, tick, world, regen_per_tick=0):

        # store world
        self.world = world

        # initial store data
        self.__capacity = game_object_json['capacity'].copy()
        self.__initial_used_capacity = game_object_json['used_capacity']
        self.regen_per_tick = regen_per_tick

        # initial parameters
        self.__initial_tick = tick

        # dynamic parameters
        self.reservations = {}

    def __str__(self):
        return f'source with contents {self.__initial_used_capacity.items()}'

    @property
    def currently_full(self, resource_type):
        if self.__initial_used_capacity[resource_type] < self.__current_capacity[resource_type]:
            return False
        else:
            return True

    @property
    def contents(self):
        contents = self.__initial_used_capacity.copy()
        for tick in range(self.__initial_tick, self.__current_tick):
            if tick in self.reservations:
                for reservation in self.reservations[tick]:
                    contents[reservation['resource_type']] += reservation['amount']
            if self.regen_per_tick != 0:
                for resource_type in contents:
                    if contents[resource_type] < self.__capacity[resource_type]:
                        contents[resource_type] += self.regen_per_tick

        return contents

    def test_reservation(self, tick, test_reservation):

        # initialize good reservation and see if it fails a test
        good_reservation = True

        # init contents to beginning
        contents = self.__initial_used_capacity.copy()

        # loop through all ticks
        for tick in range(self.__initial_tick, tick + 1):

            # process reservations
            if tick in self.reservations:
                for reservation in self.reservations[tick]:
                    contents[reservation['resource_type']] += reservation['amount']

            # process new reservation
            if int(tick) == int(test_reservation['tick']):
                contents[test_reservation['resource_type']] += test_reservation['amount']

            # regeneration if applicable
            if self.regen_per_tick != 0:
                for resource_type in contents:
                    if contents[resource_type] < self.__capacity[resource_type]:
                        contents[resource_type] += self.regen_per_tick

            # test for goodness
            for resource_type in contents:
                if contents[resource_type] < 0:
                    good_reservation = False

        return good_reservation


class Spawn(GameObject):

    def __init__(self, *args, **kwargs):

        # run parent init
        GameObject.__init__(self, *args, **kwargs)
        self.static_object = True
        self.passable = False

    def __str__(self):
        return f'spawn named {self.universal_id} and store {self.store}'

    @property
    def spawn_point(self):
        # TODO: calc a more realistic spawn point
        return self.world.point(x=self.starting_location.x, y=self.starting_location.y + 1)

    def spawn_creep(self, body, tick):

        # init spawned bool
        spawned_creep = None

        # create variables associated with creep spawn
        reservation = {
            'amount': creep_body_resource_cost(body) * -1,
            'tick': tick,
            'resource_type': 'energy'
        }
        number_of_ticks = creep_body_resource_cost(body)

        # check if the spawn is busy
        if not self.busy(tick=tick, number_of_ticks=number_of_ticks):

            # check if it has enough energy
            if self.store.test_reservation(reservation):

                # assign reservation for energy
                if tick not in self.store.reservations:
                    self.store.reservations[tick] = []
                self.store.reservations[tick].append(reservation)

                # assign actions for creep creation
                task = {
                    'received': False,
                    'tick': tick,
                    'assigned_to': self.universal_id,
                    'type': 'spawnCreep',
                    'desired_return_value': 0,
                    'details': {
                        'body': body,
                        'name': uuid.uuid4().hex
                    }
                }
                self.add_task(task)

                # create creep json object
                spawn_pt = self.spawn_pt
                creep_json = {
                    'name': task['details']['name'],
                    'detailed_body': [{'type': body_part, 'hits': 100, 'boost': None} for body_part in body],
                    'code_type': 'creep',
                    'pos': {'room_name': spawn_pt.js_room_name, 'x': spawn_pt.room_x, 'y': spawn_pt.room_y}
                }

                # create creep
                spawned_creep = Creep(snapshot_json=creep_json, tick=tick, world=self.world, player=self.player)

                # TODO: add creep to the objects

                # assign wait options for length of build
                for loop_tick in range(tick + 1, tick + number_of_ticks):
                    task = {
                        'received': False,
                        'tick': loop_tick,
                        'assigned_to': self.universal_id,
                        'type': 'wait',
                        'desired_return_value': 99,
                        'details': {}
                    }
            self.add_task(task)

            # return status

        return spawned_creep


class Flag(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
        self.passable = True


class Source(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)

    @property
    def harvest_location(self):
        # TODO: search for storage near it first, otherwise pick where storage should go
        print(f'path from {self.starting_location} and path to {self.kingdom_flag.starting_location}')
        path_to_flag = self.starting_location.path_to(to_point=self.kingdom_flag.starting_location)
        print(f'returned path is {path_to_flag}')
        return path_to_flag[1]
