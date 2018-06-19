from __future__ import unicode_literals
import os.path
import time
import xbmc
import xbmcvfs

from resources.lib.helpers import addon, timestamp_to_str, str_to_timestamp, load_data, save_data, FileError
from resources.lib.tasks import BaseTask, TaskError, TaskJSONRPCError, TaskFileError, TaskScriptError
from resources.lib.helpers.jsonrpc import exec_jsonrpc, JSONRPCError

class ImportTaskError(TaskError):
    pass
class ImportTaskJSONRPCError(ImportTaskError,TaskJSONRPCError):
    pass
class ImportTaskFileError(ImportTaskError, TaskFileError):
    pass
class ImportTaskScriptError(ImportTaskError, TaskScriptError):
    pass

class ImportTask(BaseTask):
    LAST_IMPORT_FILE = 'last_import.tmp'

    def __init__(self, video_type, ignore_script = False, silent = False, last_import = None):
        super(ImportTask, self).__init__('import', video_type, ignore_script, silent)
        # try to get the last_import datetime either from arg, or the tmp file stored in addon data location; fallback to the Epoch
        try:
            last_import_from_file = str_to_timestamp(load_data(self.LAST_IMPORT_FILE))
        except FileError, Exception:
            last_import_from_file = 0
        self.last_import = last_import or last_import_from_file
        self.this_run = time.time() # save run date of the current task, to override last_import on success
        self.save_resume_point = True # save run timestamp if task is successful

    # called when process completed; typically used for setting the result
    # returns: TaskResult object
    def on_process_finished(self, result):
        # optionally clean library
        if (addon.getSettingBool('movies.import.autoclean') and result.nb_modified > 0):
            try:
                self.log.info('automatically cleaning the library...')
                exec_jsonrpc('VideoLibrary.Clean')
            except JSONRPCError as e:
                # just log the error
                self.log.warning('error cleaning the library: %s' % str(e))

        # if we do not save the resume point, then we will not notify the user
        if (not self.save_resume_point):
            return

        # if everything is fine, save the run datetime as the new import resume point
        if (not result.script_errors and not result.errors):
            try:
                self.log.debug('saving last_import to data file \'%s\'' % self.LAST_IMPORT_FILE)
                # save this_run datetime to last_import.tmp
                save_data(self.LAST_IMPORT_FILE, timestamp_to_str(self.this_run))
            except FileError as e:
                self.log.warning('error saving last_import datetime to data file \'%s\': %s' % (e.path, e))
                self.log.warning('  => next import will probably process the same videos again!')
                result.warnings.append('cannot save import resume point')
        else:
                self.log.debug('NOT saving last_import to data file \'%s\', as there were some errors' % self.LAST_IMPORT_FILE)
