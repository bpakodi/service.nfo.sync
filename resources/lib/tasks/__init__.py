from threading import Thread as BaseThread
from Queue import Empty
import os.path

import xbmc
import xbmcvfs

from resources.lib.helpers import plural, Error
from resources.lib.helpers.log import Logger
from resources.lib.helpers.jsonrpc import notify
import resources.lib.library as Library
LibraryError = Library.LibraryError # just as a convenience
from resources.lib.script import FileScriptHandler, ScriptError
from resources.lib.nfo import NFOHandler, NFOLoadHandler, NFOHandlerError


################################################
### thread class, in charge of running tasks ###
################################################
# see multithreading example: https://forum.kodi.tv/showthread.php?tid=165223

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
                task._run_from_thread()
                self.tasks.task_done()
            except Empty:
                # Allow other stuff to run
                xbmc.sleep(100)

#############################################################
### task result class, useful to hold everything together ###
#############################################################

class TaskResult(object):
    def __init__(self, status = 'idle', lines = []):
        self.status = status
        self.title = ''
        self.lines = lines if (isinstance(lines, list)) else [ lines ]
        # we keep a track of some info here
        self.nb_items = 0
        self.modified = []
        self.errors = []
        self.warnings = []
        self.script_errors = False # tracked globally, not in errors

    @property
    def nb_modified(self):
        return len(self.modified)
    @property
    def nb_errors(self):
        return len(self.errors)
    @property
    def nb_warnings(self):
        return len(self.warnings)

    def add_error(self, nfo, ex):
        self.errors.append([ nfo.nfo_path, str(ex) ])

    # build the title and lines depending on results
    def build(self):
        if (self.nb_items == 0):
            self.lines = [ 'nothing to process' ]
            return self.status
        if (self.status != 'complete'):
            return self.status

        if (self.nb_items == 1 and self.nb_errors > 0):
                # we consider status failed
                self.status = 'failed'

        self.title = '%s: %s processed' % (self.status, plural('video', self.nb_items))

        # process errors
        nfo_tokens = [ '%s modified' % plural('NFO') ]
        if (self.nb_errors) > 0):
            nfo_tokens.append('%s' % plural('error', self.nb_errors))
        self.lines.append(', '.join(nfo_tokens))

        if (result.script_errors):
            self.lines.append('script errors: see logs')

#######################
### task base class ###
#######################

class TaskError(Error):
    pass
class TaskJSONRPCError(TaskError):
    pass
# base class for task exceptions with a path
class TaskPathError(TaskError):
    def __init__(self, path, err_msg, ex = None):
        super(TaskPathError, self).__init__(err_msg, ex)
        self.path = path
class TaskFileError(TaskPathError):
    pass
class TaskScriptError(TaskPathError):
    pass

# Base class for tasks, to be derived for each video type: movies, tvshow, season, episode
class BaseTask(object):
    def __init__(self, task_family, video_type, ignore_script = False):
        # create specific logger with namespace
        self.log = Logger(self.__class__.__name__)
        self.task_family = task_family
        self.video_type = video_type
        self.ignore_script = ignore_script
        # initialize some variables
        self.items = []
        self.script = None

    @property
    def signature(self):
        return '%s %s' % (self.video_type, self.task_family)

    # that is the method that is actually called from Thread.run()
    def _run_from_thread(self):
        self.log.debug('initializing %s' % self.signature)
        self.run()

    # main processing here, could be called directly
    def run(self):
        result = self.process() # result is a TaskResult object

        self.notify_result(result, notify_user = addon.getSettingBool('movies.auto.notify'))

    def process(self):
        # collect entries we should process
        try:
            self.populate_entries()
        except TaskError as e:
            self.log.error('error populating entries => aborting task')
            return TaskResult('aborted', 'cannot populate entries, see logs')

        # early exit if nothing to process
        if (len(self.items) == 0):
            return TaskResult('complete')

        # instanciate a TaskResult object
        result = TaskResult()

        # optionally load the script we will apply on all entries
        # we load the file now, in order to bypass it later if errors are encountered
        if (not self.ignore_script):
            try:
                self.script = self.load_script()
            except ScriptError as e:
                self.log.notice(e)
                e.dump(self.log.notice)
                self.log.notice('  => ignoring script error => resuming task without script')
                self.script = None
                result.script_errors = True

        for video_id in self.items:
            # collect the nb of processed items in result
            result.nb_items += 1
            # instanciate a nfo handler; we use a loop here, as the derived class can implement some fallback strategy if a handler fails (see on_nfo_load_failed())
            while (True):
                try:
                    nfo = self.get_nfo_handler(video_id)
                    nfo.make_xml()
                    self.on_nfo_loaded(nfo, result)
                except NFOHandlerError as e:
                    self.log.warning(e)
                    e.dump(self.log.warning)
                    # try to fall back to another nfo handler
                    nfo = self.on_nfo_load_failed(nfo, result)
                    if (not nfo):
                        result.add_error(nfo, e)
                        break

            # apply script to nfo content
            if (self.script and not self.ignore_script):
                if (not self.log.apply_script(nfo)):
                    result.script_errors = True # not tracked in result.errors

            # save nfo, and trigger event if content was actually modified
            try:
                modified = nfo.save()
                if (modified):
                    self.log.info('saving nfo: \'%s\'' % nfo.nfo_path)
                    if (self.on_nfo_saved(nfo, result)):
                        result.modified.append(nfo.nfo_path) # add to processed only if saved
                else:
                    self.log.debug('not saving to \'%s\': contents are identical' % nfo.nfo_path)
            except NFOHandlerError as e:
                self.log.error(e)
                e.dump(self.log.error)
                result.add_error(nfo, e)

        # build the result, to set title and lines; lines may be appended in event callback
        result.status = 'complete'
        result.build()
        return self.on_process_completed(result)

    # to be overridden
    # populate the list of entries (video details) to be processed
    def populate_entries(self):
        pass

    # load script content
    def load_script(self):
        script_path = xbmc.translatePath(addon.getSetting('movies.general.script.path'))
        if (not addon.getSettingBool('movies.general.script') or not script_path):
            self.log.debug('not applying any script on nfo files')
            return None
        else:
            self.log.debug('loading script: %s' % script_path)
            return FileScriptHandler(script_path, log_prefix = self.__class__.__name__)

    # run external script to modify the XML content, if applicable
    def apply_script(self, nfo):
        if (not self.script):
            return True
        # apply script to XML content
        try:
            self.log.debug('executing script against nfo: %s' % nfo.nfo_path)
            self.script.execute(locals_dict = {
                'soup': nfo.soup,
                'root': nfo.root,
                'video_type': self.video_type,
                'video_path': nfo.video_path,
                'nfo_path': nfo.nfo_path,
                'video_title': nfo.video_title,
                'task_family': self.task_family,
            })
            return True
        except ScriptError as e:
            self.log.warning('error executing script against nfo: %s' % nfo.nfo_path)
            e.dump(self.log.warning)
            self.log.warning('  => script error, the nfo will NOT be updated')
            return False

    # can be overridden
    # instanciate the NFOHandler
    def get_nfo_handler(self, video_id):
        # by default, load content from file
        self.log.debug('instanciating NFOHandler')
        return NFOLoadHandler(self, self.video_type, video_id)

    # to be overridden
    # called when nfo content has been loaded
    def on_nfo_loaded(self, nfo, result):
        pass
    # to be overridden
    # called when nfo content has been actually saved (meaning content was modified)
    def on_nfo_saved(self, nfo, result):
        return True
    # to be overridden
    # called when an exception was caught while processing the nfo handler
    def on_nfo_load_failed(self, nfo, result):
        self.log.warning('  => no fallback NFO handler => skipping video')
        return None
    # to be overridden
    # called when process completed; typically used for last actions or tweaking the result
    # returns: TaskResult object
    def on_process_completed(self, result):
        # this method will not be called if nb_items == 0, or the process aborted
        return result

    # log (and optionally visually notify) the results on task completion
    def notify_result(self, result, notify_user = False):
        # process log
        if (result.lines):
            log_str = '%s: %s' % (title, ' / '.join(result.lines))
        else:
            log_str = title
        self.log.log(log_str, xbmc.LOGERROR if (result.nb_errors) else xbmc.LOGINFO)
        # optionally notify user
        if (notify_user):
            notify('\n'.join(result.lines), title)

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
