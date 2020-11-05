from world import World
from player import Player
from director import Director
import logging
from matplotlib import pyplot as plt
import networkx as nx

if __name__ == '__main__':

    # setup logging
    logging.basicConfig(filename='./logs/screepy.log', format='%(asctime)s\(%(levelname)s\): %(message)s',
                        level=logging.DEBUG)

    # initialize the world
    world = World('local_server.config')

    # initialize the director
    director = Director(world=world, config_file_location='local_server.config')

    # initalize players
    #director.add_player(Player(config_file_location='local_server.config', world=world))

    # test cycle
    #director.direct_single_turn()

