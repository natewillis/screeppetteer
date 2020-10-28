import networkx as nx
from screeps_utilities import room_js_row_col


class Point:

    def __init__(self, x=0, y=0, snapshot_json=None):

        # create point from either snapshot or directly
        if snapshot_json is None:
            self.x = x
            self.y = y
        else:
            self.convert_from_snapshot_json(snapshot_json)

    def convert_from_snapshot_json(self, snapshot_json):
        pass

    def __str__(self):
        return f'x:{self.x} y:{self.y}'

    def __hash__(self):
        return hash((self.x, self.y))


class Room:

    def __init__(self, row=0, col=0, room_name=None, top_left_js_row_col=None):

        # init properties
        self.__row = row
        self.__col = col

        # top left row col
        self.__top_left_js_row = 0
        self.__top_left_js_col = 0
        if top_left_js_row_col is not None:
            self.__top_left_js_row = top_left_js_row_col['row']
            self.__top_left_js_col = top_left_js_row_col['col']

        # convert room_name
        if room_name is not None:
            row_col = room_js_row_col(room_name)
            self.__row = row_col['row'] - self.__top_left_js_row
            self.__col = row_col['col'] - self.__top_left_js_col

    @property
    def row(self):
        return self.__row

    @property
    def col(self):
        return self.__col

    @property
    def js_row_col(self):
        return {'row': self.__row + self.__top_left_js_row, 'col': self.__col + self.__top_left_js_col}

    @property
    def js_room_name(self):

        # get js row col
        row_col = self.js_row_col
        room_name_row = row_col['row']
        room_name_col = row_col['col']

        # n_s
        if row_col['row'] < 0:
            n_s = 'S'
            room_name_row += 1
        else:
            n_s = 'N'

        # e_w
        if row_col['col'] < 0:
            e_w = 'W'
            room_name_col += 1
        else:
            e_w = 'E'

        return f'{e_w}{abs(room_name_row)}{n_s}{abs(room_name_col)}'

    def top_left_point(self):
        return Point(x=self.col*50, y=self.col*50)

    def point_from_terrain_index(self, terrain_index):
        return Point(x=(terrain_index - ((terrain_index//50)*50))+(self.col*50), y=(terrain_index//50)+(self.col*50))

    def __str__(self):
        return f'{self.js_room_name} object'


class Line:

    def __init__(self, points=None):
        if points is None:
            self.points == []
        else:
            self.points = points


# networkx graph of world
class Map:

    def __init__(self):
        pass
