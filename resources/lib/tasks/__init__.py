from threading import Thread as BaseThread
from Queue import Empty
import os.path

import xbmc
import xbmcvfs

from resources.lib.helpers import addon_profile
from resources.lib.helpers.log import Logger
from resources.lib.helpers.exceptions import Error
from resources.lib.helpers.jsonrpc import exec_jsonrpc, JSONRPCError, notify
from resources.lib.script import FileScriptHandler, ScriptError


# multithreading example: see https://forum.kodi.tv/showthread.php?tid=165223

class Thread(BaseThread):
    def __init__(self, queue, **kwargs):
        self.tasks = queue
        # self.running = False
        super(Thread, self).__init__(kwargs)

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        # Rather than running forever, check to see if it is still OK
        while self.running:
            try:
                # Don't block
                task = self.tasks.get(block=False)
                task._run()
                self.tasks.task_done()
            except Empty:
                # Allow other stuff to run
                xbmc.sleep(100)

class TaskError(Error):
    pass
class TaskJSONRPCError(TaskError):
    pass
# base class for task exceptions with a path
class TaskPathError(TaskError):
    def __init__(self, path, err_msg, ex = None):
        # super(TaskPathError, self).__init__()
        self.path = path
        self.err_msg = err_msg
        self.ex = ex
    def __str__(self):
        if (self.ex):
            return '%s: %s: %s' % (self.err_msg, self.ex.__class__.__name__, str(self.ex))
        else:
            return '%s' % self.err_msg

class TaskFileError(TaskPathError):
    pass
class TaskScriptError(TaskPathError):
    pass

# Base class for tasks, to be derived for each video type: movies, tvshow, season, episode
class BaseTask(object):
    # define all the possible JSON-RPC methods, for each and every video type
    JSONRPC_METHODS = {
        'movie': {
            'list': {
                'method': 'VideoLibrary.GetMovies', # JSON-RPC method
                'result_key': 'movies' # JSON data field to extract
            },
            'details': {
                'method': 'VideoLibrary.GetMovieDetails', # JSON-RPC method
                'result_key': 'moviedetails' # JSON data field to extract
            }
        },
        'set': {
            'details': {
                'method': 'VideoLibrary.GetMovieSetDetails', # JSON-RPC method
                'result_key': 'setdetails' # JSON data field to extract
            }
        }
    }

    def __init__(self, task_family, video_type):
        # create specific logger with namespace
        self.log = Logger(self.__class__.__name__)
        self.task_family = task_family
        self.video_type = video_type
        self.errors = set()

    @property
    def signature(self):
        return '%s %s' % (self.video_type, self.task_family)

    # that is the method that is actually called from Thread.run()
    def _run(self):
        self.log.debug('initializing %s' % self.signature)
        self.run()

    # main processing here, to be overriden
    def run(self):
        pass

    # get all entries from the library for the given video_type
    def get_list(self, **kwargs):
        try:
            method = self.JSONRPC_METHODS[self.video_type]['list']['method']
            result_key = self.JSONRPC_METHODS[self.video_type]['list']['result_key']
            return exec_jsonrpc(method, **kwargs)[result_key]
        except KeyError as e:
            self.log.error('cannot retrieve list of %ss: invalid key for BaseTask.JSONRPC_METHODS' % self.video_type)
            self.log.error('Error was: %s' % str(e))
            raise TaskJSONRPCError('cannot retrieve list of %ss: invalid key for BaseTask.JSONRPC_METHODS' % self.video_type)
        except JSONRPCError as e:
            self.log.error('Kodi JSON-RPC error: %s' % str(e))
            raise TaskJSONRPCError('Kodi JSON-RPC error: %s' % str(e))

    # get details for a given library entry
    def get_details(self, video_id, video_type = None, **kwargs):
        if (not video_type):
            video_type = self.video_type
        try:
            method = self.JSONRPC_METHODS[video_type]['details']['method']
            result_key = self.JSONRPC_METHODS[video_type]['details']['result_key']
            # inject the video ID in the arguments; key label is based on the video_type (+'id')
            kwargs[video_type + 'id'] = video_id
            # perform the JSON-RPC call
            return exec_jsonrpc(method, **kwargs)[result_key]
        except KeyError as e:
            self.log.error('cannot retrieve details for %s #%d: invalid key for BaseTask.JSONRPC_METHODS' % (video_type, video_id))
            self.log.error('Error was: %s' % str(e))
            raise TaskJSONRPCError('cannot retrieve details for %s #%d: invalid key for BaseTask.JSONRPC_METHODS' % (video_type, video_id))
        except JSONRPCError as e:
            self.log.error('Kodi JSON-RPC error: %s' % str(e))
            raise TaskJSONRPCError('Kodi JSON-RPC error: %s' % str(e))

    # log (and optionally visually notify) the results on task completion
    def notify(self, msg, details = '', notify_user = False):
        # process log
        log_str = msg + ((': ' + details) if (details) else '')
        self.log.log(log_str, xbmc.LOGERROR if (self.errors) else xbmc.LOGINFO)
        # optionally notify user
        if (notify_user):
            notify_str = msg + (('\n' + details) if (details) else '')
            notify(notify_str)

    # run external python script in a given context
    # args:
    #   locals_dict: locals, see exec documentation for help
    def exec_script_file(self, script_path, locals_dict = {}):
        # initialize and execute the script
        try:
            self.log.debug('initializing script: \'%s\'' % script_path)
            script = FileScriptHandler(script_path, log_prefix = self.__class__.__name__)
            self.log.debug('executing script: \'%s\'' % script_path)
            script.execute(locals_dict = locals_dict)
            self.log.debug('script executed: \'%s\'' % script_path)
        except ScriptError as e:
            raise TaskScriptError(script_path, str(e))



# A dummy task, useful for testing
class SleepTask(BaseTask):
    def __init__(self, duration=4):
        self.duration = duration

    def run(self):
        self.log.debug('SleepTask: sleeping for %s s' % self.duration)
        xbmc.sleep(self.duration * 1000)
        self.log.debug('SleepTask: done sleeping for %s s' % self.duration)
