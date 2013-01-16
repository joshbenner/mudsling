

class Error(Exception):
    def __init__(self, msg=""):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class InvalidObject(Error):
    def __init__(self, obj=None, msg="Invalid Object"):
        super(InvalidObject, self).__init__(msg)
        self.obj = obj
