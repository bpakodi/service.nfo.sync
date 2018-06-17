import xbmcvfs
from resources.lib.helpers.exceptions import Error
from resources.lib.helpers.log import Logger

class ScriptError(Error):
    pass
class ScriptExecError(ScriptError):
    def __init__(self, err_msg, ex = None):
        self.err_msg = err_msg
        self.ex = ex
    def __str__(self):
        if (self.ex):
            return '%s: %s: %s' % (self.err_msg, self.ex.__class__.__name__, str(self.ex))
        else:
            return '%s' % self.err_msg
class ScriptFileError(ScriptError):
    pass

# base script handler class
# able to execute some raw script if given on constructor
class ScriptHandler(object):
    def __init__(self, content = None, log_prefix = ''):
        # create specific logger with namespace
        self.log = Logger(self.signature)
        try:
            self.content = str(content)
        except:
            raise ScriptError('invalid content')

    # to be overridden
    @property
    def label(self):
        return 'raw'
    @property
    def signature(self):
        return 'script[%s]' % self.label

    def execute(self, locals_dict = {}):
        # check that we have content at least
        if (not self.content):
            self.log.warning('empty content => nothing to execute')
            return

        # preset the locals dict
        _locals_dict = {
            'log': self.log,
        }
        # apply additional locals from arguments
        for k, v in locals_dict.iteritems():
            _locals_dict[k] = v

        # do the actual code execution
        try:
            exec(self.content, {}, _locals_dict)
        except Exception as e:
            raise ScriptExecError('script error', e)

# file script handler
class FileScriptHandler(ScriptHandler):
    def __init__(self, path, log_prefix = ''):
        self.path = path # as it is used by signature => by self.log
        super(FileScriptHandler, self).__init__(log_prefix = log_prefix)
        # try to load the file
        # check if the file already exists
        if (not xbmcvfs.exists(self.path)):
            raise ScriptFileError('script file does not exist')
        # open it, and set content from it
        try:
            fp = xbmcvfs.File(self.path)
            self.content = fp.read()
            fp.close()
        except Exception as e:
            raise ScriptFileError('cannot load content script from file')

    @property
    def label(self):
        return 'file: \'%s\'' % self.path
