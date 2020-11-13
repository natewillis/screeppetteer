import configparser
import constants
from screeps_utilities import creep_body_spawn_time

# logging
import logging

logger = logging.getLogger(__name__)


class Director:
    def __init__(self, world, config_file_location):

        # get username and password from safe file
        config = configparser.ConfigParser()
        config.read(config_file_location)

        # get parameters
        self.frozen_ticks = int(config['DIRECTOR']['frozen_ticks'])
        self.future_ticks = int(config['DIRECTOR']['future_ticks'])
        self.seconds_per_cycle = config['DIRECTOR']['seconds_per_cycle']

        # grab other arguments
        self.world = world
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    def player_names(self):
        return [player.player_name for player in self.players]

    @property
    def kingdom_flags(self):
        return [flag for flag in self.world.game_objects.values() if
                flag.specific_type == 'flag' and flag.color == constants.COLOR_RED]

    @property
    def kingdom_names(self):
        return [flag.name for flag in self.kingdom_flags]

    def kingdom_controllers(self):
        flag_rooms = [flag.location(flag.snapshot_tick()).room.js_room_name for flag in self.kingdom_flags]
        return [controller for controller in self.world.game_objects.values() if controller.location(
            controller.snapshot_tick).room.js_room_name in flag_rooms and controller.specific_type == 'controller']

    def kingdom_game_objects(self, kingdom_flag):
        game_objects = []
        for game_object in self.world.game_objects.values():
            closest_flag = min(self.kingdom_flags,
                               key=lambda flag: game_object.starting_location.range(flag.starting_location))
            if closest_flag.name == kingdom_flag.name:
                game_objects.append(game_object)
        return game_objects

    @property
    def first_tick(self):
        return min([player.snapshot_tick for player in self.players])

    @property
    def start_tick(self):
        return self.first_tick + self.frozen_ticks

    @property
    def end_tick(self):
        return self.first_tick + self.future_ticks

    def direct_single_turn(self, saved_snapshot=None):

        # clear world objects
        self.world.init_new_turn()

        # get data from current ick
        for player in self.players:
            # object data
            player.get_snapshot(saved_snapshot)

        # get earliest tick
        first_tick = self.first_tick
        start_tick = self.start_tick
        end_tick = self.end_tick
        logger.info(f'running turn from {first_tick} to {end_tick} with unfrozen tick as {start_tick}')

        # clear out old tasks
        for player in self.players:
            player.tasks = dict(filter(lambda task: first_tick <= int(task[0]) < start_tick, player.tasks.items()))

        # process jobs (once the creep has a task assigned, it cant be changed)
        # tasks are the criteria that determine if a job has been filled)
        # need to account for uncreated objects so far
        # TODO: Enemy SA

        # jobs are assign per game controller
        for kingdom_flag in self.kingdom_flags:

            logger.info(f'running tasks for {kingdom_flag.name}')

            # pre-collect some objects
            player = kingdom_flag.player
            pre_kingdom_objects = self.kingdom_game_objects(kingdom_flag)
            sources = [source for source in pre_kingdom_objects if source.specific_type == 'source']

            # sort sources to put closest first
            sources.sort(key=lambda source: source.starting_location.range(kingdom_flag.starting_location))
            for source in sources:
                logger.info(
                    f'source {source.js_id} is range {source.starting_location.range(kingdom_flag.starting_location)}')

            # TODO: seperate actions for controllers at level 0

            ############ ENERGY Planning ###########
            # setup loop
            tick = start_tick - 1
            logger.info(f'loop from {tick} to {end_tick}')
            while tick <= end_tick:

                # increment tick
                tick += 1
                ticks_until_end = end_tick - tick
                logger.info(f'energy loop on tick {tick}')

                # get state of world
                kingdom_game_objects = self.kingdom_game_objects(kingdom_flag)
                my_creeps = player.my_creeps(tick=tick, kingdom_flag=kingdom_flag)
                logger.info(f'there are total of {len(my_creeps)} live creeps')
                spawns = [spawn for spawn in kingdom_game_objects if
                          spawn.specific_type == 'spawn' and spawn.owner == kingdom_flag.owner]

                # Level 0: Energy Harvest Without Storage
                harvest_level = 0
                harvest_creep = constants.BASIC_UTILITY_CREEP

                # Level 1: Energy Harvest With Storage And Minimum Harvester (BASIC_UTILITY_CREEP)

                # Level 2: Energy Harvest With Storage And Maximum Harvester (HARVEST_CREEP)

                #
                harvest_creeps = [creep for creep in my_creeps if creep.body == harvest_creep]
                logger.info(f'there are {len(harvest_creeps)} potential harvest creeps on tick {tick}')

                # harvest from sources and throw in container or carry
                viable_sources = []
                if harvest_level == 0:
                    # harvest level 0 means only the closest source
                    viable_sources.append(sources[0])

                # assign creep to each viable source
                for source in viable_sources:

                    # source information
                    harvest_pt = source.harvest_location

                    # loop through creeps to see if any are currently harvesting here
                    source_harvested = False
                    for creep in harvest_creeps:
                        logger.info(f'checkin harvest creep {creep.universal_id} if hes harvesting')
                        creep_task_list = creep.task(tick)
                        if creep_task_list is not None:
                            for creep_task in creep_task_list:
                                if creep_task is not None:
                                    if creep_task['type'] == 'harvest':
                                        if creep_task['details']['target'] == source.js_id:
                                            source_harvested = True
                                            break
                    if source_harvested:
                        logger.info(f'{source.js_id} is harvested on tick {tick}')
                        continue

                    # get unassigned creeps who can do this job
                    unassigned_creeps = [creep for creep in harvest_creeps if not creep.busy(tick, ticks_until_end)]

                    # init harvest creep assignment
                    assigned_harvest_creep = None

                    # need to spawn one
                    if len(unassigned_creeps) == 0:

                        # spawn the creep
                        # TODO: loop backward to test previous positions if the current doesnt work
                        # TODO: figure out how long its going to take to get to the task
                        harvest_creep_spawn_time = creep_body_spawn_time(harvest_creep)

                        for spawn in spawns:

                            # where would the creep spawn from
                            spawn_pt = spawn.spawn_point

                            # the fastest it could be ready to harvest is body spawn time (likely longer due to travel)
                            new_creep_start_harvest = 1e10
                            new_creep_spawn_start = tick - (harvest_creep_spawn_time + spawn_pt.range(harvest_pt)) + 1

                            # loop until the new creep gets there at the right time
                            while new_creep_start_harvest > tick and new_creep_spawn_start >= start_tick:
                                if new_creep_start_harvest == 1e10:
                                    new_creep_spawn_start -= 1
                                else:
                                    new_creep_spawn_start -= max(1, abs(new_creep_spawn_start - tick))
                                (path, path_ticks) = self.world.path_for_body_at_time(
                                    body=harvest_creep,
                                    from_point=spawn_pt,
                                    to_point=harvest_pt,
                                    start_tick=(new_creep_spawn_start + harvest_creep_spawn_time + 1)
                                )
                                new_creep_start_harvest = path_ticks[-1]

                            logger.info(
                                f'harvest creep spawning should start at {new_creep_spawn_start} in order to harvest at {new_creep_start_harvest} with goal of {tick}')

                            # if the loop was able to get the creep there at the right time, spawn it
                            if new_creep_start_harvest <= tick and new_creep_spawn_start >= start_tick:
                                assigned_harvest_creep = spawn.spawn_creep(body=harvest_creep,
                                                                           spawn_start_tick=new_creep_spawn_start)
                                if assigned_harvest_creep is not None:
                                    # we did it!, now tell him to get to the harvest area
                                    logger.info(f'harvesting with path {path}')
                                    logger.info(f'path ticks: {path_ticks}')
                                    assigned_harvest_creep.assign_path(path=path, path_ticks=path_ticks)
                                    break

                    else:
                        # TODO: sort by who's closest
                        assigned_harvest_creep = unassigned_creeps[0]

                        # TODO: assign closest creep and propagate creep forward
                        (path, path_ticks) = self.world.path_for_body_at_time(
                            body=assigned_harvest_creep.body,
                            from_point=assigned_harvest_creep.location(tick),
                            to_point=harvest_pt,
                            start_tick=tick
                        )
                        assigned_harvest_creep.assign_path(path=path, path_ticks=path_ticks)

                        logger.info(f'ticks to live is {assigned_harvest_creep.ticks_to_live}')

                    if assigned_harvest_creep is not None:
                        assigned_harvest_creep.harvest_til_death(start_tick=path_ticks[-1], target=source)

            ############ Energy delivery #################

            # setup loop
            tick = start_tick - 1
            logger.info(f'energy delivery loop from {tick} to {end_tick}')
            while tick <= end_tick:

                # increment tick
                tick += 1
                ticks_until_end = end_tick - tick
                logger.info(f'energy delivery loop on tick {tick}')

                # world state variables
                kingdom_game_objects = self.kingdom_game_objects(kingdom_flag)
                spawns = [spawn for spawn in kingdom_game_objects if
                          spawn.specific_type == 'spawn' and spawn.owner == kingdom_flag.owner]

                # refresh creep variables
                transport_carry_capacity = constants.BASIC_DELIVERY_CREEP.count('carry') * constants.CARRY_CAPACITY
                my_creeps = player.my_creeps(kingdom_flag=kingdom_flag, tick=tick)
                delivery_creeps = [creep for creep in my_creeps if creep.body == constants.BASIC_DELIVERY_CREEP]

                if harvest_level == 0:
                    refill_sources = [creep for creep in my_creeps if creep.body == harvest_creep]

                # TODO: calc number of delivery creeps
                required_delivery_creeps = len(refill_sources)

                logger.info(f'we need {required_delivery_creeps} delivery creeps to be full')

                if len(refill_sources) > 0:

                    if len(delivery_creeps) < required_delivery_creeps:

                        delivery_creep_spawn_time = creep_body_spawn_time(constants.BASIC_DELIVERY_CREEP)

                        for spawn in spawns:

                            # the fastest it could be ready to harvest is body spawn time
                            new_creep_spawn_start = tick - delivery_creep_spawn_time

                            # try and build one for this turn
                            if new_creep_spawn_start >= start_tick:
                                logger.info(f'trying to build a new delivery creep')
                                new_delivery_creep = spawn.spawn_creep(
                                    body=constants.BASIC_DELIVERY_CREEP,
                                    spawn_start_tick=new_creep_spawn_start
                                )
                                logger.info(f'result is building of {new_delivery_creep}')
                                if new_delivery_creep is not None:
                                    logger.info(
                                        f'before new creep transfers it has empty space of {new_delivery_creep.store_empty_space(tick)}')
                                    new_delivery_creep.refill_resource(target=refill_sources[0],
                                                                       start_tick=new_creep_spawn_start + delivery_creep_spawn_time + 1)
                                    logger.info(
                                        f'after new creep transfers it has empty space of {new_delivery_creep.store_empty_space(tick)}')
                                    break

                    # assign job to creeps
                    my_creeps = player.my_creeps(kingdom_flag=kingdom_flag, tick=tick)
                    delivery_creeps = [creep for creep in my_creeps if creep.body == constants.BASIC_DELIVERY_CREEP]

                    # refill any empty transports
                    for delivery_creep in delivery_creeps:
                        logger.info(f'creep has {delivery_creep.store_empty_space(tick=tick)} empty space')
                        if delivery_creep.store_empty_space(tick=tick) >= transport_carry_capacity:
                            if not delivery_creep.busy(tick=tick, number_of_ticks=delivery_creep.death_tick - tick):
                                logger.info(
                                    f'refilling {delivery_creep.universal_id} because it isnt busy from {tick} and onward {delivery_creep.death_tick - tick}')
                                delivery_creep.refill_resource(
                                    target=refill_sources[0],
                                    start_tick=tick
                                )

                    logger.info(f'there are {len(delivery_creeps)} delivery creeps')
                    # keep the spawn supplied
                    for spawn in spawns:
                        logger.info(f'spawn empty space is {spawn.store_empty_space(tick=tick)}')
                        if spawn.store_empty_space(tick=tick) >= transport_carry_capacity:
                            logger.info(
                                f'going to try and deliver energy to spawn with 1 of the {len(delivery_creeps)} creeps')
                            for delivery_creep in delivery_creeps:
                                if delivery_creep.delivery_round_trip(
                                        resource='energy',
                                        amount=transport_carry_capacity,
                                        target_object=spawn,
                                        delivery_tick=tick,
                                        earliest_start_tick=start_tick
                                ):
                                    continue

            ############ Basic Spawn Upgrade #############
            # setup loop
            tick = start_tick - 1
            logger.info(f'controller upgrade loop from {tick} to {end_tick}')
            while tick <= end_tick:

                # increment tick
                tick += 1
                ticks_until_end = end_tick - tick
                logger.info(f'basic controller upgrade loop on tick {tick}')

                # world state variables
                kingdom_game_objects = self.kingdom_game_objects(kingdom_flag)
                spawns = [spawn for spawn in kingdom_game_objects if
                          spawn.specific_type == 'spawn' and spawn.owner == kingdom_flag.owner]
                controllers = [controller for controller in kingdom_game_objects if
                               controller.specific_type == 'controller' and controller.owner == kingdom_flag.owner]
                controller = None
                if len(controllers) == 0:
                    logger.info(f'no controllers on tick {tick}')
                    continue
                else:
                    controller = controllers[0]

                # refresh my creeps
                my_creeps = player.my_creeps(kingdom_flag=kingdom_flag, tick=tick)

                if harvest_level == 0:
                    refill_sources = [creep for creep in my_creeps if creep.body == harvest_creep]
                    dedicated_upgrade_creeps = 1
                    upgrade_body = constants.BASIC_UTILITY_CREEP

                # figure out how many potential upgrade creeps we can draw from
                logger.info(f'we need {dedicated_upgrade_creeps} upgrade creeps to be full')
                upgrade_creeps = [creep for creep in my_creeps if
                                  creep.body == upgrade_body]
                upgrade_carry_capacity = upgrade_body.count('carry') * constants.CARRY_CAPACITY

                # check if the correct number of upgrade creeps have an upgrade coming up
                actual_upgrade_creeps = 0
                non_upgrade_creeps = []
                for upgrade_creep in upgrade_creeps:
                    upgrade_creep_tasks = upgrade_creep.tasks
                    this_creep_is_upgrading = False
                    for upgrade_tick in upgrade_creep_tasks:
                        for task in upgrade_creep_tasks[upgrade_tick]:
                            if task['type'] == 'upgrade_controller':
                                this_creep_is_upgrading = True
                                break
                        if this_creep_is_upgrading:
                            break
                    if this_creep_is_upgrading:
                        actual_upgrade_creeps += 1
                    else:
                        non_upgrade_creeps.append(upgrade_creep)

                # check if we need more creeps upgrading
                if actual_upgrade_creeps < dedicated_upgrade_creeps:

                    # calc spawn details
                    spawn_start_tick = tick - creep_body_spawn_time(upgrade_body)

                    # we need to spawn a creep to do upgrading for the rest of its life
                    for spawn in spawns:

                        # see if the spawn can do it
                        new_upgrade_creep = spawn.spawn_creep(body=upgrade_body,
                                                              spawn_start_tick=spawn_start_tick)

                        if new_upgrade_creep is not None:

                            # where would the creep spawn from
                            spawn_pt = spawn.spawn_point

                            # TODO: devise a better way of selecting refill sources
                            # refill this creep with energy to start
                            new_upgrade_creep.refill_resource(target=refill_sources[0], start_tick=tick)

                            # figure out when we're not busy
                            start_upgrading_tick = tick
                            while not new_upgrade_creep.busy(start_upgrading_tick,
                                                             new_upgrade_creep.death_tick - start_upgrading_tick) and start_upgrading_tick < self.end_tick:
                                start_upgrading_tick += 1

                            # set it to upgrade forever and ever
                            while not new_upgrade_creep.busy(start_upgrading_tick,
                                                             new_upgrade_creep.death_tick - start_upgrading_tick) and start_upgrading_tick < self.end_tick:
                                new_upgrade_creep.delivery_round_trip(
                                    resource='energy', amount=upgrade_carry_capacity,
                                    target_object=controller,
                                    delivery_tick=start_upgrading_tick, earliest_start_tick=self.start_tick)
                                start_upgrading_tick += 1

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

            # Energy Delivery

        # commit tasks
        for player in self.players:
            player.commit_tasks()
