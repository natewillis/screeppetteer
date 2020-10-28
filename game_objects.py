class GameObject:
    def __init__(self):
        self.type = ''


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
