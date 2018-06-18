from __future__ import unicode_literals
import os.path
import time
import xbmc
import xbmcvfs

from resources.lib.helpers import addon, timestamp_to_str, str_to_timestamp, load_data, save_data
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

    def __init__(self, video_type, ignore_script = False, last_import = None):
        super(ImportTask, self).__init__('import', video_type, ignore_script)
        # try to get the last_import datetime either from arg, or the tmp file stored in addon data location; fallback to the Epoch
        try:
            last_import_from_file = str_to_timestamp(load_data(self.LAST_IMPORT_FILE))
        except TaskFileError, Exception:
            last_import_from_file = 0
        self.last_import = last_import or last_import_from_file
        self.this_run = time.time() # save run date of the current task, to override last_import on success
        self.save_resume_point = True # save run timestamp if task is successful

    # called when nfo content has been actually saved (meaning content was modified)
    def on_nfo_saved(self, nfo, result):
        # refresh entry as it was modified
        # note: Kodi will actually perform delete + add operations, which will result in a new entry id in the lib
        try:
            self.log.debug('refreshing %s: %s (%d)' % (nfo.video_type, nfo.video_title, nfo.video_id))
            result = exec_jsonrpc('VideoLibrary.RefreshMovie', movieid=nfo.video_id, ignorenfo=False)
            if (result != 'OK'):
                self.log.warning('%s refresh failed for \'%s\' (%d)' % (self.video_type, nfo.video_path, nfo.video_id))
                result.add_error(nfo, 'refresh failed')
                return False
            return True
        except JSONRPCError as e:
            self.log.warning('%s refresh failed for \'%s\' (%d)' % (self.video_type, nfo.video_path, nfo.video_id))
            self.log.warning(e)
            result.add_error(nfo, 'refresh failed: %s' % str(e))
            return False

    # called when process completed; typically used for setting the result
    # returns: TaskResult object
    def on_process_completed(self, result):
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
            return result

        # if everything is fine, save the run datetime as the new import resume point
        if (not result.script_errors and not result.errors):
            try:
                self.log.debug('saving last_import to data file \'%s\'' % self.LAST_IMPORT_FILE)
                # save this_run datetime to last_import.tmp
                save_data(self.LAST_IMPORT_FILE, timestamp_to_str(self.this_run))
            except TaskFileError as e:
                self.log.warning('error saving last_import datetime to data file \'%s\': %s' % (e.path, e))
                self.log.warning('  => next import will probably process the same videos again!')
                result.lines.append('warning: cannot save import resume point')
        else:
                self.log.debug('NOT saving last_import to data file \'%s\', as there were some errors' % self.LAST_IMPORT_FILE)
