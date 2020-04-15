class PunchDummy:
    def something(self):
        pass


class PunchDummy2(PunchDummy):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value
