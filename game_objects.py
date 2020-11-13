import uuid
from world import Point
import constants
from screeps_utilities import creep_body_resource_cost, delta_from_direction, creep_body_spawn_time

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
        self.ticks_to_live = game_object_json['ticks_to_live'] if 'ticks_to_live' in game_object_json else None
        self.static_object = True
        self.passable = False

        # special parameters
        self.store = Store(game_object_json=game_object_json['store'],
                           tick=tick, world=world) if 'store' in game_object_json else None
        if self.store is None:
            logger.info(f'{self.code_type} has no store')
        else:
            logger.info(f'{self.code_type} has a store')

        # specific type is the combo of structure type and code_type
        self.specific_type = ''
        if self.structure_type is None:
            self.specific_type = self.code_type
        else:
            self.specific_type = self.structure_type

        # dynamic parameters
        # TODO: get initial location converted
        self.__initial_location = self.world.point(snapshot_json=game_object_json['pos'])
        self.__initial_tick = tick
        self.__initial_hits = game_object_json['hits'] if 'hits' in game_object_json else None
        self.initial_fatigue = game_object_json['fatigue'] if 'fatigue' in game_object_json else None

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

    def alive(self, tick):
        return True

    def task(self, tick):
        if tick in self.tasks:
            return self.tasks[tick]
        else:
            return None

    def add_task(self, task):

        # add common task data
        task['received'] = False
        task['execution_output'] = ''

        # add the task
        logger.info(f'adding task {task}')
        if task['tick'] not in self.player.tasks:
            logger.info(f'adding empty task dict')
            self.player.tasks[task['tick']] = {}
        if self.universal_id not in self.player.tasks[task['tick']]:
            self.player.tasks[task['tick']][self.universal_id] = []
        self.player.tasks[task['tick']][self.universal_id].append(task)

    def location(self, tick):
        return self.__initial_location

    @property
    def starting_location(self):
        return self.__initial_location

    def __str__(self):
        return f'Game Object: {self.specific_type} with id of {self.universal_id} initialized at tick {self.__initial_tick}'

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
            return f'{self.structure_type}-{self.starting_location.room.js_room_name}-{self.starting_location.js_x}-{self.starting_location.js_y}'
        elif self.code_type == 'source':
            return f'{self.js_id}'
        elif self.code_type == 'creep':
            return f'{self.name}'
        elif self.code_type == 'flag':
            return f'{self.name}'

    def busy(self, tick, number_of_ticks=1):
        logger.info(f'running busy check for {self.universal_id} from {tick} forward {number_of_ticks}')
        # init return
        busy = False

        # only owned objects can be busy with tasks
        logger.info(f'busy creep is owned by {self.owner}')
        if self.owner is None:
            logger.info(f'{self.universal_id} has no owner, returning false on busy check')
            return False

        # get task queue
        tasks = self.player.tasks

        # loop through period to see if tasks
        busy_tick = None
        for busy_tick in range(tick, tick + number_of_ticks):
            if busy_tick in tasks:
                # my tasks
                if self.universal_id in tasks[busy_tick]:
                    logger.info(f'busy: there are {len(tasks[busy_tick][self.universal_id])} tasks on tick {busy_tick} for {self.universal_id}')
                    if len(tasks[busy_tick][self.universal_id]) > 0:
                        logger.info('this means im busy!')
                        busy = True
                        break
                # if a creep wants to give me energy, i'm busy that turn
                if self.code_type == 'creep':
                    for universal_id in tasks[busy_tick]:
                        task_list = tasks[busy_tick][universal_id]
                        for task in task_list:
                            if task['type'] == 'transfer':
                                if task['details']['target'] == self.universal_id:
                                    logger.info('transfer to me means im busy')
                                    busy = True
                                    break


        # return busy
        logger.info(f'{self.universal_id} was {busy} for busy at ending at {busy_tick} with end of {tick+number_of_ticks}')
        return busy

    @property
    def kingdom_flag(self):

        # only players have kingdom flags
        if self.player is None:
            return None

        # find closest flag
        return min(self.player.kingdom_flags, key=lambda flag: self.starting_location.range(flag.starting_location))

    @property
    def body(self):
        body = []
        # TODO: account for hits and boost
        if self.detailed_body is not None:
            for body_detail in self.detailed_body:
                body.append(body_detail['type'])
        return body

    def test_store_related_task(self, test_store_related_task):

        good_task = True
        # test the game object that you called this from
        if not self.store_contents(query_tick=self.player.director.end_tick, test_store_related_task=test_store_related_task):
            good_task = False

        # test any target game objects
        if 'target' in test_store_related_task['details']:
            target = self.world.game_objects[test_store_related_task['details']['target']]
            if target.store is not None:
                if not target.store_contents(query_tick=self.player.director.end_tick, test_store_related_task=test_store_related_task):
                    good_task = False

        # return final answer
        return good_task

    def store_contents(self, query_tick, test_store_related_task=None):

        logger.info(f'starting store content calc or {self.specific_type} from {self.snapshot_tick} to {query_tick}')

        # check if i have a store
        if self.store is None:
            if test_store_related_task is None:
                return {}
            else:
                return False

        # initialize good task and see if it fails a test
        good_task = True

        # init contents to beginning
        contents = self.store.initial_used_capacity_copy
        logger.info('initial contents')
        for resource_type in contents:
            logger.info(f'{resource_type} = {contents[resource_type]}')

        # loop through all ticks
        for tick in range(self.snapshot_tick, query_tick):

            # regeneration if applicable (has to happen first)
            if self.store.regen_per_tick != 0:
                for resource_type in contents:
                    if contents[resource_type] < self.store.max_capacity(resource_type):
                        contents[resource_type] = min(contents[resource_type] + self.store.regen_per_tick,
                                                      self.store.max_capacity(resource_type))

            # hold all tasks for this tick in a list
            tasks_to_process = []

            # process all tasks to see if i'm the source or target
            if tick in self.player.tasks:
                for task_list in self.player.tasks[tick].values():
                    for task in task_list:
                        # tasks I complete
                        if task['assigned_to'] == self.universal_id:
                            tasks_to_process.append(task)
                        # tasks that affect me
                        elif 'target' in task['details']:
                            if task['details']['target'] == self.universal_id:
                                tasks_to_process.append(task)

            # add new task to process list
            if test_store_related_task is not None:
                if int(tick) == int(test_store_related_task['tick']):
                    tasks_to_process.append(test_store_related_task)

            # process tasks
            for task in tasks_to_process:
                # transfer task
                if task['type'] == 'transfer':
                    if task['assigned_to'] == self.universal_id:
                        contents[task['details']['resource_type']] -= task['details']['amount']
                        logger.info(f'decrementing {task["details"]["resource_type"]} {task["details"]["amount"]}')
                    elif task['details']['target'] == self.universal_id:
                        logger.info(f'incrementing {task["details"]["amount"]}')
                        contents[task['details']['resource_type']] += task['details']['amount']

                # spawnCreep task
                if task['type'] == 'spawnCreep':

                    # calculate energy details
                    cost = creep_body_resource_cost(task['details']['body'])

                    # remove it from the spawn
                    contents['energy'] -= cost
                    logger.info(f'decrementing {cost}')

                if task['type'] == 'harvest':

                    # calculate harvest amount
                    work_parts = self.body.count('work')
                    harvest_per_action = work_parts * 2

                    # TODO: make this work for more than energy sources
                    contents['energy'] += harvest_per_action
                    if contents['energy'] > self.store.max_capacity('energy'):
                        contents['energy'] = self.store.max_capacity('energy')


                    # withdraw task
                    # drop task
                    # pickup task
                    # build task
                    # repair task

            # test for goodness
            # logger.info(f'store contents of {self.specific_type} at {tick} are {contents["energy"]}')
            for resource_type in contents:
                if contents[resource_type] < 0:
                    logger.info(f'store contents of {self.specific_type} at {tick} are {contents["energy"]}')
                    good_task = False
        
        logger.info(f'expected contents of {self.specific_type} at {query_tick} are {contents}')
        
        if test_store_related_task is None:
            return contents
        else:
            return good_task

    def store_empty_space(self, tick):

        # get contents
        contents = self.store_contents(query_tick=tick)
        logger.info(f'empty check shows {contents}')

        # add up all types of used capacity
        resource_total = 0
        for resource_type in contents:
            resource_total += contents[resource_type]

        # subtract from max
        return self.store.overall_max_capacity - resource_total


class Creep(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
        self.static_object = False

    def location(self, tick):

        # make sure theyre not asking for something unreasonable
        if tick < self.snapshot_tick or tick > self.death_tick:
            return None

        # get tasks
        tasks = self.tasks

        # init location
        current_location = self.starting_location
        for current_tick in range(self.snapshot_tick, tick):
            if current_tick in tasks:
                task_list = tasks[current_tick]
                for task in task_list:
                    if task['type'] == 'move':
                        direction = task['details']['direction']
                        delta = delta_from_direction(direction)
                        current_location = Point(x=(current_location.x + delta['x']), y=(current_location.y + delta['y']),
                                                 world=self.world)

        # return propagated location
        return current_location

    def assign_path(self, path, path_ticks):
        if len(path) <= 1:
            return False
        logger.info(f'assigning path of length {len(path)}')
        for pt_num in range(1, len(path)):
            logger.info(f'working point {pt_num}')

            # create move task
            task = {
                'tick': path_ticks[pt_num-1],
                'assigned_to': self.universal_id,
                'type': 'move',
                'desired_return_value': 0,
                'console_output': f'{self.universal_id} moving to {path[pt_num].js_x_y}',
                'details': {
                    'direction': path[pt_num-1].move_direction_to_point(path[pt_num]),
                }
            }
            self.add_task(task)
        return True

    @property
    def death_tick(self):
        return self.snapshot_tick + self.ticks_to_live

    def alive(self, tick):
        if tick > self.death_tick or tick < self.snapshot_tick:
            return False
        else:
            return True

    def harvest_til_death(self, start_tick, target):

        harvest_per_turn = self.body.count('work') * 2
        harvest_until_tick = min(self.death_tick, self.player.director.end_tick)
        logger.info(f'harvesting from {start_tick} to death ({harvest_until_tick})')

        for harvest_tick in range(start_tick, harvest_until_tick):
            task = {
                'tick': harvest_tick,
                'assigned_to': self.universal_id,
                'type': 'harvest',
                'desired_return_value': 0,
                'details': {
                    'target': target.js_id,
                    'resource': 'energy',
                    'amount': harvest_per_turn
                }
            }
            self.add_task(task)

    def fatigue(self, tick):

        # make sure theyre not asking for something unreasonable
        if tick < self.snapshot_tick or tick > self.death_tick:
            return None

        # get tasks
        tasks = self.tasks

        # calc body fatigue stats
        fatigue_per_move = len([body_part for body_part in self.body if body_part != 'move'])
        fatigue_recovery_per_tick = self.body.count('move') * 2

        # init location
        current_fatigue = self.initial_fatigue

        for current_tick in range(self.snapshot_tick, tick):

            if current_fatigue > 0:
                current_fatigue -= min(current_fatigue, fatigue_recovery_per_tick)

            if current_tick in tasks:
                task_list = tasks[current_tick]
                for task in task_list:
                    if task['type'] == 'move':
                        direction = task['details']['direction']
                        delta = delta_from_direction(direction)
                        current_location = Point(x=(current_location.x + delta['x']), y=(current_location.y + delta['y']),
                                                 world=self.world)
                        current_fatigue += int(current_location.terrain) * fatigue_per_move

        # this turns fatigue recovery
        current_fatigue -= min(current_fatigue, fatigue_recovery_per_tick)

        # return propagated fatigue
        return current_fatigue

    def delivery_round_trip(self, resource, amount, target_object, delivery_tick,
                            earliest_start_tick):

        logger.info(f'initiating delivery of {resource} from {self.universal_id} to {target_object.universal_id} on {delivery_tick}')

        # init return bool
        successful_trip = False

        # transport variables
        transport_carry_capacity = self.body.count('carry') * constants.CARRY_CAPACITY
        source_universal_id = None
        source_object = None

        # in order to complete this task, i'd have to be not busy at least at delivery time,
        # full up
        if self.busy(delivery_tick):
            logger.info(f'{self.universal_id} was busy so couldnt deliver to {target_object.universal_id} on {delivery_tick}')
            return successful_trip
        if self.store_contents(query_tick=delivery_tick)[resource] < transport_carry_capacity:
            logger.info(f'{self.universal_id} wasnt full so couldnt deliver to {target_object.universal_id} on {delivery_tick}')
            return successful_trip

        # get locations
        target_location = target_object.location(delivery_tick)

        # the fastest it could be ready to harvest is body spawn time (likely longer due to travel)
        estimated_delivery_tick = 1e10
        delivery_start_tick = delivery_tick - self.location(delivery_tick).range(target_location) + 2

        # calc radius to target
        radius_to_target = 1
        if target_object.specific_type == 'controller':
            radius_to_target = 3

        # loop until the new creep gets there at the right time
        while estimated_delivery_tick > delivery_tick and delivery_start_tick >= earliest_start_tick:
            if estimated_delivery_tick == 1e10:
                delivery_start_tick -= 1
            else:
                delivery_start_tick -= max(1, abs(estimated_delivery_tick - delivery_tick))
            logger.info(f'trying delivery start of {delivery_start_tick}')
            (delivery_path, delivery_path_ticks) = self.world.path_for_body_at_time(
                body=self.body,
                from_point=self.location(delivery_start_tick),
                to_point=target_location,
                start_tick=delivery_start_tick,
                radius=radius_to_target,
                path_finding_object=self
            )
            estimated_delivery_tick = delivery_path_ticks[-1]

        # check if we successfully got to the target at the right time
        logger.info(f'round trip delivery path optimization returned estimated delivery of {estimated_delivery_tick} '
                    f'with need of {delivery_tick} and delivery start of {delivery_start_tick} with earliest of {earliest_start_tick}')
        if estimated_delivery_tick == delivery_tick and delivery_start_tick >= earliest_start_tick:

            # check if we're busy for the trip to the target
            if not self.busy(tick=delivery_start_tick, number_of_ticks=(delivery_tick-delivery_start_tick)):

                #logging
                logger.info(f'{self.universal_id} was not busy from {delivery_start_tick} to {delivery_tick-delivery_start_tick}')

                # figure out what source we need
                for game_object in self.player.director.kingdom_game_objects(self.kingdom_flag):
                    if game_object.specific_type == 'storage':
                        if game_object.location(delivery_tick).range(self.location(delivery_tick)) <= 1:
                            source_universal_id = game_object.universal_id
                            break
                    elif game_object.specific_type == 'creep':
                        if game_object.alive(delivery_tick):
                            if game_object.body == constants.BASIC_UTILITY_CREEP or game_object.body == constants.HARVEST_CREEP:
                                if game_object.location(delivery_start_tick).range(self.location(delivery_tick)) <= 1:
                                    source_universal_id = game_object.universal_id
                                    break
                logger.info(f'delivery found return fillup source of {source_universal_id}')
                if source_universal_id is None:
                    return successful_trip
                else:
                    source_object = self.world.game_objects[source_universal_id]

                # calc source location
                source_location = source_object.location(delivery_tick)

                # calc what time we can start the trip back
                transfer_to_target_start_tick = delivery_path_ticks[-1]+1
                if source_object.specific_type == 'controller':
                    return_trip_start_tick = transfer_to_target_start_tick +(transport_carry_capacity/(self.body.count('work')))
                else:
                    return_trip_start_tick = transfer_to_target_start_tick + 1

                # calc radius to source (usually 1 i think)
                radius_to_source = 1

                # now check if we can get back to fill up before we're busy again
                (return_path, return_path_ticks) = self.world.path_for_body_at_time(
                    body=self.body,
                    from_point=delivery_path[-1],
                    to_point=source_location,
                    start_tick=return_trip_start_tick,
                    radius=radius_to_source,
                    path_finding_object=self
                )
                return_to_refill_tick = return_path_ticks[-1]
                refill_tick = return_path_ticks[-1] + 1
                logger.info(f'{self.universal_id} will return to refill at {return_to_refill_tick} and do the refill at {refill_tick}')

                # check if its correct
                if return_path[-1].range(source_location) <= radius_to_source:

                    # check if we're not busy until we get back
                    if not self.busy(delivery_start_tick, refill_tick-delivery_start_tick):

                        # final check is to make sure i can fill myself up from the source
                        test_result = False
                        if source_object.code_type == 'creep':
                            transfer_from_source_to_creep_task = {
                                'tick': refill_tick,
                                'assigned_to': source_object.universal_id,
                                'type': 'transfer',
                                'desired_return_value': 0,
                                'details': {
                                    'target': self.universal_id,
                                    'resource_type': resource,
                                    'amount': self.store.overall_max_capacity
                                }
                            }
                            test_result = source_object.test_store_related_task(test_store_related_task=transfer_from_source_to_creep_task)
                        else:
                            transfer_from_source_to_creep_task = {
                                'tick': refill_tick,
                                'assigned_to': self.universal_id,
                                'type': 'withdraw',
                                'desired_return_value': 0,
                                'details': {
                                    'target': source_object.universal_id,
                                    'resource_type': resource,
                                    'amount': amount
                                }
                            }
                            test_result = self.test_store_related_task(test_store_related_task=transfer_from_source_to_creep_task)

                        if test_result:

                            # we can do it!

                            # delivery path
                            self.assign_path(path=delivery_path, path_ticks=delivery_path_ticks)

                            # transfer to target
                            if target_object.specific_type == 'controller':
                                for upgrade_tick in range(transfer_to_target_start_tick, transport_carry_capacity/self.body.count('work')):
                                    transfer_to_target_task = {
                                        'tick': upgrade_tick,
                                        'assigned_to': self.universal_id,
                                        'type': 'upgrade_controller',
                                        'desired_return_value': 0,
                                        'details': {
                                            'target': target_object.universal_id,
                                        }
                                    }
                                    logger.info(f'upgrade_controller tick {upgrade_tick}')
                                    self.add_task(transfer_to_target_task)
                            else:
                                transfer_to_target_task = {
                                    'tick': transfer_to_target_start_tick,
                                    'assigned_to': self.universal_id,
                                    'type': 'transfer',
                                    'desired_return_value': 0,
                                    'details': {
                                        'target': target_object.universal_id,
                                        'resource_type': resource,
                                        'amount': amount
                                    }
                                }
                                logger.info('delivery round trip transfer')
                                self.add_task(transfer_to_target_task)

                            # return to source
                            self.assign_path(path=return_path, path_ticks=return_path_ticks)

                            # withdraw from source
                            logger.info('round trip transfer from source to creep')
                            if source_object.code_type == 'creep':
                                source_object.add_task(transfer_from_source_to_creep_task)
                            else:
                                self.add_task(transfer_from_source_to_creep_task)

                            # we were successful
                            successful_trip = True

        # return final result
        return successful_trip

    def refill_resource(self, target, resource='energy', start_tick=None, end_tick=None):

        # transport variables
        transport_carry_capacity = self.body.count('carry') * constants.CARRY_CAPACITY

        if start_tick is not None:

            # get to source
            (path, path_ticks) = self.world.path_for_body_at_time(
                body=self.body,
                from_point=self.location(start_tick),
                to_point=target.location(start_tick),
                start_tick=start_tick,
                radius=1,
                path_finding_object=self
            )
            logger.info('refill move')
            self.assign_path(path=path, path_ticks=path_ticks)
            logger.info(f'at the end of this i think im at {self.location(path_ticks[-1]).js_x_y} while the path is {path[-1].js_x_y}')

            # get refilled
            valid_task = False
            transfer_tick = path_ticks[-1]+1
            while not valid_task:

                # check if the source has enough energy
                test_result = False
                if target.code_type == 'creep':
                    refill_task = {
                        'tick': transfer_tick,
                        'assigned_to': target.universal_id,
                        'type': 'transfer',
                        'desired_return_value': 0,
                        'details': {
                            'target': self.universal_id,
                            'resource_type': resource,
                            'amount': min(
                                target.store_contents(query_tick=transfer_tick)[resource],
                                self.store.max_capacity(resource)
                            )
                        }
                    }
                    test_result = target.test_store_related_task(test_store_related_task=refill_task)
                else:
                    refill_task = {
                        'tick': transfer_tick,
                        'assigned_to': target.universal_id,
                        'type': 'withdraw',
                        'desired_return_value': 0,
                        'details': {
                            'target': target.universal_id,
                            'resource_type': resource,
                            'amount': min(
                                target.store_contents(query_tick=transfer_tick)[resource],
                                self.store.max_capacity(resource)
                            )
                        }
                    }
                    test_result = self.test_store_related_task(test_store_related_task=refill_task)

                if test_result:
                    valid_task = True
                    break
                else:
                    transfer_tick += 1

            if valid_task:

                # get resource from target
                logger.info('refill transfer/withdraw')
                if target.code_type == 'creep':
                    target.add_task(refill_task)
                else:
                    self.add_task(refill_task)


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

    def __str__(self):
        return f'source with contents {self.__initial_used_capacity.items()}'

    @property
    def initial_used_capacity_copy(self):
        return self.__initial_used_capacity.copy()

    @property
    def overall_max_capacity(self):
        resource_max = 0
        for resource_type in self.__capacity:
            resource_max += self.__capacity[resource_type]
        return resource_max

    def max_capacity(self, resource_type):
        return self.__capacity[resource_type]


class Spawn(GameObject):

    def __init__(self, *args, **kwargs):

        # run parent init
        GameObject.__init__(self, *args, **kwargs)
        self.static_object = True
        self.passable = False
        self.store.regen_per_tick = 1

    def __str__(self):
        return f'spawn named {self.universal_id} and store {self.store}'

    @property
    def spawn_point(self):
        # TODO: calc a more realistic spawn point
        return self.world.point(x=self.starting_location.x, y=self.starting_location.y + 1)

    def spawn_creep(self, body, spawn_start_tick):

        # init spawned bool
        spawned_creep = None

        # create variables associated with creep spawn
        creep_creation_task = {
            'tick': spawn_start_tick,
            'assigned_to': self.universal_id,
            'type': 'spawnCreep',
            'desired_return_value': 0,
            'details': {
                'body': body,
                'name': uuid.uuid4().hex
            }
        }
        number_of_ticks = creep_body_spawn_time(body)

        # check if the spawn is busy
        if not self.busy(tick=spawn_start_tick, number_of_ticks=number_of_ticks):

            # check if it has enough energy
            if self.test_store_related_task(test_store_related_task=creep_creation_task):

                # assign reservation for energy
                self.add_task(creep_creation_task)

                # create creep json object
                spawn_pt = self.spawn_point
                creep_json = {
                    'name': creep_creation_task['details']['name'],
                    'detailed_body': [{'type': body_part, 'hits': 100, 'boost': None} for body_part in body],
                    'code_type': 'creep',
                    'pos': {'room_name': spawn_pt.room.js_room_name, 'x': spawn_pt.js_x, 'y': spawn_pt.js_y},
                    'ticks_to_live': 1500,
                    'owner': self.player.player_name,
                    'store': {
                        'capacity': {
                            'energy': body.count('carry') * constants.CARRY_CAPACITY
                        },
                        'free_capacity': {
                            'energy': body.count('carry') * constants.CARRY_CAPACITY
                        },
                        'used_capacity': {
                            'energy': 0
                        }
                    }
                }

                # create creep
                spawned_creep = Creep(game_object_json=creep_json, tick=spawn_start_tick+number_of_ticks, world=self.world, player=self.player)
                logger.info(f'spawned creep has owner {spawned_creep.owner}')
                # TODO: add creep to the objects

                # assign wait options for length of build
                for loop_tick in range((spawn_start_tick + 1), (spawn_start_tick + number_of_ticks)):
                    task = {
                        'tick': loop_tick,
                        'assigned_to': self.universal_id,
                        'type': 'wait',
                        'desired_return_value': 99,
                        'details': {}
                    }
                    self.add_task(task)

                # return status
                self.world.game_objects[spawned_creep.universal_id] = spawned_creep

        return spawned_creep


class Flag(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
        self.passable = True


class Source(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
        self.__harvest_location_cache = None

    @property
    def harvest_location(self):
        # TODO: search for storage near it first, otherwise pick where storage should go
        if self.__harvest_location_cache is None:
            path_to_flag = self.starting_location.path_to(to_point=self.kingdom_flag.starting_location, include_static_objects=True, ignore_terrain_differences=True)
            harvest_point = self.world.point(x=path_to_flag[1][0], y=path_to_flag[1][1])
            self.__harvest_location_cache = harvest_point
        else:
            harvest_point = self.__harvest_location_cache
        return harvest_point


class Controller(GameObject):

    def __init__(self, *args, **kwargs):
        GameObject.__init__(self, *args, **kwargs)
        self.passable = False