class SuperStop:
    """
    This class resolves the issue TypeError: object.__init__() takes exactly one argument by being the last class
    in a mro and ommitting all arguments. This should be always last in the mro()!
    """

    def __init__(self, *args, **kwargs):
        mro = self.__class__.mro()
        if SuperStop in mro:
            if len(mro) - 2 != mro.index(SuperStop):
                raise ValueError("SuperStop ommitting arguments in " + str(self.__class__)
                                 + " super() callstack: " + str(mro))
        super().__init__()
