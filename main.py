from game import Game

if __name__ == '__main__':

    # initialize a single game
    game = Game()

    # get snapshot
    game.get_snapshot()

    print(game.game_objects)