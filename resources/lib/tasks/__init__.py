from threading import Thread as BaseThread
from Queue import Empty
import os.path

import xbmc
import xbmcvfs

from resources.lib.helpers import addon_profile
from resources.lib.helpers.log import Logger
from resources.lib.helpers.exceptions import Error
from resources.lib.helpers.jsonrpc import exec_jsonrpc, JSONRPCError, notify


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

    def __init__(self, monitor, task_type, video_type):
        # create specific logger with namespace
        self.log = Logger(self.__class__.__name__)
        self.task_type = task_type
        self.video_type = video_type
        self.monitor = monitor
        self.errors = []

    # that is the method that is actually called from Thread.run()
    def _run(self):
        self.log.debug('initializing %s %s' % (self.video_type, self.task_type))
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
            raise TaskError('cannot retrieve list of %ss: invalid key for BaseTask.JSONRPC_METHODS: %s' % (self.video_type, str(e)))
        except JSONRPCError as e:
            self.log.error(str(e))

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
            raise TaskError('cannot retrieve details for %s #%d: invalid key for BaseTask.JSONRPC_METHODS: %s' % (video_type, video_id, str(e)))
        except JSONRPCError as e:
            self.log.error(str(e))

    # log (and optionally visually notify) the results on task completion
    def notify(self, msg, details = '', notify_user = False):
        # process log
        log_str = msg + ((': ' + details) if (details) else '')
        self.log.log(log_str, xbmc.LOGERROR if (self.errors) else xbmc.LOGINFO)
        # optionally notify user
        if (notify_user):
            notify_str = msg + (('\n' + details) if (details) else '')
            notify(notify_str)

    # helper methods: load / save to addon data location
    # load data from file
    def load_file(self, path, dir = ''):
        full_path = os.path.join(dir, path) if dir else path
        # check if the nfo file already exists
        if (not xbmcvfs.exists(full_path)):
            raise TaskFileError(full_path, 'file does not exist')
        # open and read from it
        try:
            fp = xbmcvfs.File(full_path)
            data = fp.read()
            fp.close()
            return data
        except Exception as e:
            raise TaskFileError(path, 'cannot load file', e)
    # save data to file
    def save_file(self, path, data, dir = ''):
        full_path = os.path.join(dir, path) if dir else path
        try:
            fp = xbmcvfs.File(full_path, 'w')
            result = fp.write(data.encode('utf-8'))
            fp.close()
        except Exception as e:
            raise TaskFileError(path, 'cannot save file', e)

        # it seems xbmcvfs does not raise any exception...
        if (not result):
            raise TaskFileError(path, 'cannot save file: unknown error')
    # load data from data file
    def load_data(self, path):
        return self.load_file(path, dir = addon_profile)
    # save data to data file
    def save_data(self, path, data):
        self.save_file(path, data, dir = addon_profile)
    # load soup from nfo file (XML)
    def load_nfo(self, nfo_path, root_tag):
        # load raw data from file (may throw exceptions)
        raw = self.load_file(nfo_path) # already contains the full path
        # load XML tree from file content
        try:
            soup = BeautifulSoup(raw, 'html.parser')
            root = soup.find(root_tag)
        except Exception as e:
            raise TaskFileError(nfo_path, 'invalid nfo file: not a valid XML document', e)

        # check if the XML content is valid
        if (root is None):
            raise TaskFileError(nfo_path, 'invalid nfo file: no root tag \'%s\'' % root_tag)
        # everything OK, return
        return (soup, root)

    # save soup tag to nfo file (XML)
    def save_nfo(self, nfo_path, root):
        try:
            content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            content = content + root.prettify_with_indent(encoding='utf-8')
            self.save_file(nfo_path, content.decode('utf-8'))
        except TaskFileError:
            raise
        except Exception as e:
            raise TaskFileError(nfo_path, 'cannot save nfo file', e)

    # execute a python script
    # args:
    #   locals_dict: locals, see exec documentation for help
    #   locals_dict: locals, see exec documentation for help
    def exec_script(self, script, globals_dict = {}, locals_dict = {}):
        try:
            exec(script, globals_dict, locals_dict)
            return True
        except Exception as e:
            raise TaskScriptError('script/path/here', 'error while executing script', e)

# A dummy task, useful for testing
class SleepTask(BaseTask):
    def __init__(self, duration=4):
        self.duration = duration

    def run(self):
        self.log.debug('SleepTask: sleeping for %s s' % self.duration)
        xbmc.sleep(self.duration * 1000)
        self.log.debug('SleepTask: done sleeping for %s s' % self.duration)

# Monkey-patch BeautifulSoup, to allow a nicer pretty print
# see https://stackoverflow.com/questions/47879140/how-to-prettify-html-so-tag-attributes-will-remain-in-one-single-line
# and https://code.i-harness.com/en/q/b70e4
from bs4 import BeautifulSoup, Tag
import re

def prettify_with_indent(self, indent_width = 4, single_lines = True, encoding=None, formatter='minimal'):
    # # compact attrs
    # if single_lines:
    #     for tag in self():
    #         for attr in tag.attrs:
    #             # print(tag.attrs[attr], tag.attrs[attr].__class__)
    #             tag.attrs[attr] = " ".join(
    #                 tag.attrs[attr].replace("\n", " ").split())
    # get prettify() before applying modifications
    output = self.prettify(encoding, formatter)
    # compact nodes
    if single_lines:
        r = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        output = r.sub('>\g<1></', output)

    # set indentation
    r = re.compile(r'^(\s*)', re.MULTILINE)
    return r.sub(r'\1' * indent_width, output)

BeautifulSoup.prettify_with_indent = prettify_with_indent
Tag.prettify_with_indent = prettify_with_indent
