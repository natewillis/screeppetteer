import unittest
import world

# logging
import logging
logger = logging.getLogger(__name__)


# point methods
class TestPointMethods(unittest.TestCase):

    def setUp(self):
        print('setting up tests for point object')
        self.world = world.World(config_file_location='local_server.config')

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



if __name__ == '__main__':
    unittest.main()









