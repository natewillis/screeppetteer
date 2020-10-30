import configparser
import uuid
import constants

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
        return [flag for flag in self.world.game_objects.values() if flag.specific_type == 'flag' and flag.color == constants.COLOR_RED]

    @property
    def kingdom_names(self):
        return [flag.name for flag in self.kingdom_flags]

    def kingdom_controllers(self):
        flag_rooms = [flag.location(flag.snapshot_tick()).room.js_room_name for flag in self.kingdom_flags]
        return [controller for controller in self.world.game_objects.values() if controller.location(controller.snapshot_tick).room.js_room_name in flag_rooms and controller.specific_type == 'controller']

    def kingdom_game_objects(self, kingdom_flag):
        game_objects = []
        for game_object in self.world.game_objects.values():
            closest_flag = min(self.kingdom_flags, key=lambda flag: game_object.starting_location.range(flag.starting_location))
            if closest_flag.name == kingdom_flag.name:
                game_objects.append(game_object)
        return game_objects

    def direct_single_turn(self):

        # clear world objects
        self.world.init_new_turn()

        # get data from current ick
        for player in self.players:
            # object data
            player.get_snapshot()

        # get earliest tick
        first_tick = min([player.snapshot_tick for player in self.players])
        start_tick = first_tick + self.frozen_ticks
        end_tick = first_tick + self.future_ticks
        print(f'running turn from {first_tick} to {end_tick} with unfrozen tick as {start_tick}')

        # clear out old tasks
        for player in self.players:
            player.tasks = dict(filter(lambda task: first_tick <= int(task[0]) < start_tick, player.tasks.items()))




        # process jobs (once the creep has a task assigned, it cant be changed)
        # tasks are the criteria that determine if a job has been filled)
        # need to account for uncreated objects so far
        # TODO: Enemy SA
        for game_object in self.world.game_objects.values():
            print(game_object)
        print(self.kingdom_flags)
        # jobs are assign per game controller
        for kingdom_flag in self.kingdom_flags:
            print(f'running tasks for {kingdom_flag.name}')
            # pre-collect some objects
            pre_kingdom_objects = self.kingdom_game_objects(kingdom_flag)
            sources = [source for source in pre_kingdom_objects if source.specific_type == 'source']

            # sort sources to put closest first
            sources.sort(key=lambda source: source.starting_location.range(kingdom_flag.starting_location))

            # TODO: seperate actions for controllers at level 0

            ############ ENERGY Planning ###########
            # setup loop
            tick = start_tick - 1
            while tick <= end_tick:

                # increment tick
                tick += 1

                # get state of world
                kingdom_game_objects = self.kingdom_game_objects(kingdom_flag)
                all_of_my_creeps = [creep for creep in kingdom_game_objects if creep.specific_type == 'creep' and creep.owner == kingdom_flag.owner]
                spawns = [spawn for spawn in kingdom_game_objects if spawn.specific_type == 'spawn' and spawn.owner == kingdom_flag.owner]

                # Level 0: Energy Harvest Without Storage
                harvest_level = 0
                harvest_creep = constants.BASIC_UTILITY_CREEP

                # Level 1: Energy Harvest With Storage And Minimum Harvester (BASIC_UTILITY_CREEP)

                # Level 2: Energy Harvest With Storage And Maximum Harvester (HARVEST_CREEP)

                #

                # harvest from sources and throw in container or carry
                viable_sources = []
                if harvest_level == 0:
                    # harvest level 0 means only the closest source
                    viable_sources.append(sources[0])
                    print(f'screep should harvest from {viable_sources[0].js_id} of {len(viable_sources)} viable sources out of {len(sources)} total sources seen')


                # assign creep to each viable source
                for source in viable_sources:
                    # TODO: look into looking at prior job assignment
                    # get unassigned creeps who can do this job
                    unassigned_creeps = []  # TODO: actually get the unassigned creeps

                    if len(unassigned_creeps) > 0:

                        # TODO: sort by who's closest

                        # TODO: assign closest creep and propagate creep forward
                        pass
                    else:
                        # assign a spawn queue position for this job
                        assigned_spawn = False
                        for spawn in spawns:
                            if spawn.store.currently_full('energy'):
                                # assign creation of creep to this spawn

                                assigned_spawn = True
                                break
                        pass


                # filter


                # Energy delivery
                    # if energy_harvest_state is zero, use utility creep, else delivery creep
                    # keep the spawn supplied

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

        # placeholder code for testing spawns
        for player in self.players:
            for tick in range(player.snapshot_tick + self.frozen_ticks, player.snapshot_tick + self.future_ticks):

                # add tick if needed
                if tick not in player.tasks:
                    player.tasks[tick] = {}

                # add spawn tasks
                player.tasks[tick]['320727bab8b0c3b'] = {
                    'recieved': False,
                    'type': 'spawnCreep',
                    'details': {
                        'body': ['move'],
                        'name': uuid.uuid4().hex
                    }
                }

        # commit tasks
        for player in self.players:
            pass
            #player.commit_tasks()
