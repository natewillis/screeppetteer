import uuid
from world import Point
import constants
from screeps_utilities import creep_body_resource_cost, delta_from_direction

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
        self.store = Store(game_object_json=game_object_json['store'], tick=tick) if 'store' in game_object_json else None


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

    @property
    def player(self):
        players = [player for player in self.world.players if player.player_name == self.owner]
        if len(players) == 0:
            return None
        else:
            return players[0]

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
        for tick in range(tick, tick+number_of_ticks):
            if tick in tasks:
                busy = True

        # return busy
        return busy


class Creep(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)

    def location(self, tick):

        # make sure theyre not asking for something unreasonable
        if tick < self.snapshot_tick:
            return None

        # get tasks
        tasks = self.tasks

        # init location
        current_location = self.starting_location
        for current_tick in range(self.snapshot_tick, tick-1):
            if current_tick in tasks:
                task = tasks[current_tick]
                if task['type'] == 'move':
                    direction = task['details']['direction']
                    delta = delta_from_direction(direction)
                    current_location = Point(x=(current_location.x+delta['x']), y=(current_location.y+delta['y']), world=self.world)

        # return propagated locaiton
        return current_location


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
        return f'source with contents {self.__current_capacity.items()}'

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
                    if contents[resource_type] <  self.__capacity[resource_type]:
                        contents[resource_type] += self.regen_per_tick

        return contents

    def test_reservation(self, tick, test_reservation):

        # initialize good reservation and see if it fails a test
        good_reservation = True

        # init contents to beginning
        contents = self.__initial_used_capacity.copy()

        # loop through all ticks
        for tick in range(self.__initial_tick, tick+1):

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

    def __str__(self):
        return f'spawn named {self.nice_id()} and store {self._GameObject__store}'

    def spawn_creep(self, body, tick):

        # init spawned bool
        spawned = True

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
                    {
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
                }
                self.add_task(task)

                #TODO: add creep to the objects


                # assign wait options for length of build
                for loop_tick in range(tick+1, tick+number_of_ticks):
                    task = {
                        {
                            'received': False,
                            'tick': loop_tick,
                            'assigned_to': self.universal_id,
                            'type': 'wait',
                            'desired_return_value': 99,
                            'details': {}
                        }
                    }
                    self.add_task(task)

        # return status
        return spawned

class Flag(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)


class Source(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
