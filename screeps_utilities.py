import re


def create_screepy_id(id="unknown", name="unknown", type="unknown"):
    return f'{type}|{name}|{id}'


def room_js_row_col(room_name):

    # E0N0 is 0,0
    # init return variables
    # its better to ask forgiveness than permission
    try:

        # do regexp
        matches = re.search(r'([WE])(\d+)([NS])(\d+)', room_name.upper())

        # calc row
        row = abs(int(matches.group(2)))
        if matches.group(1) == 'W':
            row = (row + 1) * -1

        # calc col
        col = abs(int(matches.group(4)))
        if matches.group(3) == 'S':
            col = (col + 1) * -1

    except AttributeError:

        # no match
        row = None
        col = None

    return {'row': row, 'col': col}
