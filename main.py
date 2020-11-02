from world import World
from player import Player
from director import Director
import logging

if __name__ == '__main__':

    # setup logging
    logging.basicConfig(filename='./logs/screepy.log', format='%(asctime)s\(%(levelname)s\): %(message)s',
                        level=logging.DEBUG)

    # initialize the world
    world = World('local_server.config')
    print(world.terrain.terrain_matrix)
    room_json = {'x': 4, 'y': 4, 'room_name': 'W7N7'}
    bottom_left_pt = world.point_from_js_pos(room_json)
    print(f'{room_json} is {bottom_left_pt.node} and is terrain {world.terrain.terrain_matrix[bottom_left_pt.y, bottom_left_pt.x]}')
    pt1 = world.point_from_js_pos({'x': 7, 'y': 40, 'room_name': 'W10N0'})
    pt2 = world.point_from_js_pos({'x': 40, 'y': 7, 'room_name': 'W0N10'})
    path = world.path_between(pt1, pt2, 1)
    print(len(path))


    # initialize the director
    #director = Director(world=world, config_file_location='local_server.config')

    # initalize players
    #director.add_player(Player(config_file_location='local_server.config', world=world))


    # test cycle
    #director.direct_single_turn()

    # initialize all players
    # world.add_player(Player('whazzup.config'))

    #
    # game = Game()

    # get snapshot
    # game.get_snapshot()

