class BaseException(Exception):
    def __str__(self):
        return ': '.join(self.args)

class Error(BaseException):
    pass
