import unittest
import world
import director
import player
import game_objects
import pickle

# logging
import logging
logger = logging.getLogger(__name__)

# point methods
class TestPointMethods(unittest.TestCase):

    def setUp(self):
        print('setting up tests for point object')
        self.world = world.World(config_file_location='test_server.config')

    def testPointFromXY(self):
        point = self.world.point(x=1, y=2)
        self.assertEqual(point.x, 1)
        self.assertEqual(point.y, 2)
        self.assertEqual(point.room.js_room_name, 'W10N0')
        self.assertEqual(point.js_x_y, {'x': 1, 'y': 47})
        self.assertEqual(point.edge_type, None)
        self.assertEqual(point.terrain, 255)

    def testPointFromSnapshotJson(self):
        point = self.world.point(snapshot_json={'room_name': 'W7N7', 'x': 22, 'y': 13})
        self.assertEqual(point.x, 172)
        self.assertEqual(point.y, 386)
        self.assertEqual(point.room.js_room_name, 'W7N7')
        self.assertEqual(point.js_x_y, {'x': 22, 'y': 13})
        self.assertEqual(point.edge_type, None)
        self.assertEqual(point.terrain, 255)

    def testPointEdgeCase(self):
        point = self.world.point(snapshot_json={'room_name': 'W10N1', 'x': 49, 'y': 33})
        self.assertEqual(point.x, 49)
        self.assertEqual(point.y, 66)
        self.assertEqual(point.room.js_room_name, 'W10N1')
        self.assertEqual(point.js_x_y, {'x': 49, 'y': 33})
        self.assertEqual(point.edge_type, 'E')
        self.assertEqual(point.terrain, 255.4)


# game object methods
class TestGameObjectMethods(unittest.TestCase):

    def setUp(self):

        # saved data
        self.saved_snapshots = {}
        with open('data/saved_snapshots.pickle', 'rb') as handle:
            self.saved_snapshots = pickle.load(handle)

        # world setup
        self.world = world.World(config_file_location='test_server.config')

        # initialize the director
        self.director = director.Director(world=world, config_file_location='test_server.config')

        # initalize players
        self.director.add_player(player.Player(config_file_location='test_server.config', world=world))

    def testSpawn(self):
        snapshot_json = self.saved_snapshots['basic_start_test']
        print(snapshot_json)
        spawn = game_objects.Spawn(game_object_json=snapshot_json['snapshot']['objects']['spawn-W7N7-20-11'], world=self.world, tick=snapshot_json['snapshot']['game_time'], player=self.director.players[0])
        spawn.spawn_creep(['carry', 'move'], 8224)
        print(self.director.players[0].tasks)
        self.assertEqual(spawn.universal_id, 'spawn-W7N7-20-11')
        self.assertEqual(self.director.players[0].tasks[8224]['spawn-W7N7-20-11']['type'], 'spawnCreep')
        self.assertEqual(self.director.players[0].tasks[8225]['spawn-W7N7-20-11']['type'], 'wait')



if __name__ == '__main__':
    unittest.main()








