import uuid


class GameObject:

    def __init__(self, game_object_json):
        self.id = ''
        self.type = ''

    def js_id(self):
        return self.type


class Creep(GameObject):

    def __init__(self):
        GameObject.__init__(self)


class Source(GameObject):

    def __init__(self):
        GameObject.__init__(self)


class Spawn(GameObject):

    def __init__(self):
        GameObject.__init__(self)


class Flag(GameObject):

    def __init__(self):
        GameObject.__init__(self)