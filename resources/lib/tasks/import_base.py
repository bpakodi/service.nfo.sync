from __future__ import unicode_literals
import os.path
import time
import xbmc
import xbmcvfs
from resources.lib.helpers import addon, timestamp_to_str, str_to_timestamp, get_nfo_path, load_data, save_data, load_nfo, save_nfo
from resources.lib.tasks import BaseTask, TaskError, TaskFileError, TaskScriptError
from resources.lib.helpers.jsonrpc import exec_jsonrpc, JSONRPCError
from resources.lib.script import FileScriptHandler, ScriptError

class ImportTaskError(TaskError):
    pass
class ImportTaskFileError(ImportTaskError):
    pass
class ImportTaskScriptError(ImportTaskError):
    pass
class ImportTaskJSONRPCError(ImportTaskError):
    pass

class ImportTask(BaseTask):
    LAST_IMPORT_FILE = 'last_import.tmp'

    def __init__(self, video_type, last_import = None):
        super(ImportTask, self).__init__('import', video_type)
        # try to get the last_import datetime either from arg, or the tmp file stored in addon data location; fallback to the Epoch
        try:
            last_import_from_file = str_to_timestamp(load_data(self.LAST_IMPORT_FILE))
        except TaskFileError, Exception:
            last_import_from_file = 0
        self.last_import = last_import or last_import_from_file
        self.this_run = time.time() # save run date of the current task, to override last_import on success
        self.outdated = [] # list of nfo files that are candidates for refresh
        self.save_resume_point = True # save run timestamp if task is successful

    # main task method, the task will get destroyed on exit
    def run(self):
        # will be later used when building the status string
        result_status = '%s import complete' % self.video_type
        result_details = ''
        script_error = False

        # collect entries that should be re-imported
        try:
            self.scan_outdated()
        except ImportTaskError as e:
            self.log.error('errors detected => aborting task')
            return False

        # early exit if nothing to process
        if (len(self.outdated) == 0):
            result_details = 'nothing to import'
            # log and notify user
            self.notify(result_status, result_details, addon.getSettingBool('movies.auto.notify'))
            return True

        # build the script handler object, to check if we have issues
        script = None
        # check in settings if we should run a script
        script_path = xbmc.translatePath(addon.getSetting('movies.general.script.path'))
        if (not addon.getSettingBool('movies.general.script') or not script_path):
            self.log.debug('not applying any script on imported nfo files')
        else:
            self.log.debug('applying following script on imported nfo files: %s' % script_path)
            # try to load the file, to allow bypassing it if errors are encountered
            try:
                self.log.debug('initializing script: %s' % script_path)
                script = FileScriptHandler(script_path, log_prefix = self.__class__.__name__)
            except ScriptError as e:
                self.log.notice('error loading script file: \'%s\'' % script_path)
                self.log.notice('Error was: %s' % str(e))
                self.log.notice('  => ignoring script error => proceeding with import anyway')
                script = None

        # loop through all outdated entries
        for video_details in self.outdated:
            try:
                # optionally apply a script to each of these files
                if (script and self.apply_script(script, video_details)):
                    # refresh entry if it was modified
                    self.refresh_video(video_details)
            except (ImportTaskFileError, ImportTaskJSONRPCError) as e:
                self.errors.add([ video_details['file'], str(e) ])
            except ImportTaskScriptError:
                script_error = True # tracked globally, not in errors

        # analyze results
        nb_refreshed = len(self.outdated) - len(self.errors)
        result_details = '%d refreshed' % (nb_refreshed)

        # optionally clean library
        if (addon.getSettingBool('movies.import.autoclean') and nb_refreshed > 0):
            try:
                self.log.info('automatically cleaning the library...')
                exec_jsonrpc('VideoLibrary.Clean')
            except JSONRPCError as e:
                # just log the error
                self.log.warning('error cleaning the library: %s' % str(e))

        # add some text to notification if there were some errors
        if (script_error):
            result_status += ' (with script errors)'
            result_details += '\nscript error: see log for details'

        if (self.errors):
            result_status += ' (with errors)'
            result_details += '\n%d error(s): see log for details' % (len(self.errors))

        # if we do not save the resume point, then we will not notify the user
        if (not self.save_resume_point):
            return True # even if there were some errors, the task completed

        # if everything is fine, save the run datetime as the new import resume point
        if (not script_error and not self.errors):
            try:
                self.log.debug('saving last_import to data file \'%s\'' % self.LAST_IMPORT_FILE)
                # save this_run datetime to last_import.tmp
                save_data(self.LAST_IMPORT_FILE, timestamp_to_str(self.this_run))
            except TaskFileError as e:
                self.log.warning('error saving last_import datetime to data file \'%s\': %s' % (e.path, e))
                self.log.warning('  => next import will probably process all your library again!')
                result_status += ' (with warning)'
                result_details += '\nwarning: see log for details'
        else:
                self.log.debug('NOT saving last_import to data file \'%s\', as there were some errors' % self.LAST_IMPORT_FILE)

        # log and notify user
        self.notify(result_status, result_details, addon.getSettingBool('movies.auto.notify'))
        return True

    # to be overridden
    # set the list of entries that should be imported again
    def scan_outdated(self):
        pass

    # run external script to modify the XML content, if applicable
    # returns True only if no errors was encountered, AND the XML content has been modified
    def apply_script(self, script, video_details):
        # load soup from nfo file
        try:
            video_file = video_details['file']
            nfo_path = get_nfo_path(video_file)
            (soup, root, old_raw) = load_nfo(nfo_path, self.video_type)
        except TaskFileError as e:
            self.errors.add(nfo_path)
            self.log.error('error loading nfo file: %s' % nfo_path)
            self.log.error('Error was: %s' % str(e))
            raise ImportTaskFileError(str(e))

        # apply script on XML
        try:
            self.log.debug('executing script against nfo: %s' % nfo_path)
            script.execute(locals_dict = {
                'soup': soup,
                'root': root,
                'nfo_path': nfo_path,
                'video_path': video_file,
                'video_type': self.video_type,
                'video_title': video_details['label'],
                'task_family': self.task_family,
            })
        except ScriptError as e:
            self.errors.add(nfo_path)
            self.log.notice('error executing script against nfo: %s' % nfo_path)
            self.log.error('Error was: %s' % str(e))
            self.log.notice('  => script error, current nfo will NOT be updated')
            raise ImportTaskScriptError(str(e))

        # write content to NFO file
        try:
            modified = save_nfo(nfo_path, root, old_raw)
            if (modified):
                self.log.debug('nfo saved to \'%s\'' % nfo_path)
            else:
                self.log.debug('not saving to \'%s\': contents are identical' % nfo_path)
            return modified
        except TaskFileError as e:
            self.errors.add(nfo_path)
            self.log.error('error saving nfo file: \'%s\'' % nfo_path)
            self.log.error('Error was: %s' % str(e))
            raise ImportTaskFileError(str(e))

    # refresh a single video entry
    # note: Kodi will actually perform delete + add operations, which will result in a new entry id in the lib
    def refresh_video(self, video_details):
        try:
            video_file = video_details['file']
            self.log.debug('refreshing %s: %s (%d)' % (self.video_type, video_details['label'], video_details['movieid']))
            result = exec_jsonrpc('VideoLibrary.RefreshMovie', movieid=video_details['movieid'], ignorenfo=False)
            if (result != 'OK'):
                self.errors.add(video_file)
                self.log.warning('%s refresh failed for \'%s\' (%d)' % (self.video_type, video_details['file'], video_details['movieid']))
                return False
            return True
        except JSONRPCError as e:
            self.log.error('error executing JSON-RPC query: \'%s\'' % 'VideoLibrary.RefreshMovie')
            self.log.error('Error was: %s' % str(e))
            raise ImportTaskJSONRPCError(str(e))
