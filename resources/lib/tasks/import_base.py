from __future__ import unicode_literals
import os.path
import time
import xbmc
import xbmcvfs
from resources.lib.helpers import addon
from resources.lib.tasks import BaseTask, TaskError, TaskFileError
from resources.lib.helpers.jsonrpc import exec_jsonrpc, JSONRPCError
from resources.lib.helpers import addon, timestamp_to_str, str_to_timestamp

class ImportTaskError(TaskError):
    pass

class ImportTask(BaseTask):
    LAST_IMPORT_FILE = 'last_import.tmp'
    def __init__(self, monitor, video_type, last_import = None):
        super(ImportTask, self).__init__(monitor, 'import', video_type)
        # try to get the last_import datetime either from arg, or the tmp file stored in addon data location; fallback to the Epoch
        try:
            last_import_from_file = str_to_timestamp(self.load_data(self.LAST_IMPORT_FILE))
        except TaskFileError, Exception:
            last_import_from_file = 0
        self.last_import = last_import or last_import_from_file
        self.this_run = time.time() # save run date of the current task, to override last_import on success
        self.outdated = [] # list of nfo files that are candidates for refresh


    # main task method, the task will get destroyed on exit
    def run(self):
        self.scan_library()
        self.refresh_outdated()

        # analyze results
        nb_refreshed = len(self.outdated) - len(self.errors)
        result_msg = '%s import complete' % self.video_type
        result_details = '%d refreshed' % (nb_refreshed)
        # optionally clean library
        if (addon.getSettingBool('movies.import.autoclean') and nb_refreshed > 0):
            try:
                self.log.info('automatically cleaning the library...')
                exec_jsonrpc('VideoLibrary.Clean')
            except JSONRPCError as e:
                # just log on error
                self.log.notice('error cleaning: %s' % str(e))
        # add some text to notification if there were some errors
        if (self.errors):
            result_msg += ' (with errors)'
            result_details += '\n%d error(s): see log for details' % (len(self.errors))
        else:
            # save the run datetime as the new import resume point
            try:
                self.log.debug('saving last_import to data file \'%s\'' % self.LAST_IMPORT_FILE)
                # save this_run datetime to last_import.tmp
                self.save_data(self.LAST_IMPORT_FILE, timestamp_to_str(self.this_run))
            except TaskFileError as e:
                self.log.warning('error saving last_import datetime to data file \'%s\': %s' % (e.path, e))
                self.log.warning('next import will probably process all your library!')
                result_msg += ' (with warning)'
                result_details += '\nwarning: see log for details'
        # log and notify user
        self.notify(result_msg, result_details, addon.getSettingBool('movies.auto.notify'))


    # we start by getting the list of all referenced videos of the given video_type
    # this is acceptable, because this task will be triggered AFTER library scans, which means that new nfo files are already integrated in the library
    # following this approach, all nfo that are not associated with an entry in the library can be gracefully ignored (they are probably falsy)
    def scan_library(self):
        self.log.debug('scanning library for nfo files newer than %s' % timestamp_to_str(self.last_import))
        # retrieve all video entries in the library
        videos = self.get_list(properties = ['file'])
        # TODO: handle errors / bad content. Also, what is the behaviour when library is empty?
        for video in videos:
            # check every corresponding nfo file
            self.inspect_nfo(video['file'], video)

    # inspect a nfo file to check if the corresponding video library entry should be refreshed
    def inspect_nfo(self, video_file, video_data):
        # build .nfo file name from the video one
        nfo_path = os.path.splitext(video_file)[0] + '.nfo'
        if (not xbmcvfs.exists(nfo_path)):
            return
        # get the last modified timestamp
        stat = xbmcvfs.Stat(nfo_path)
        last_modified = stat.st_mtime()
        # if the nfo file was modified after last_import, then we should refresh the corresponding video entry
        if (last_modified > self.last_import):
            last_modified_str = timestamp_to_str(last_modified)
            # this entry is outdated, add it to the list for further processing (see run())
            self.outdated.append(video_data)

    # refresh outdated video library entries
    # note: Kodi will actually perform delete + add operations, which will result in a new entry id in the lib
    def refresh_outdated(self):
        for video_data in self.outdated:
            try:
                self.log.debug('refreshing %s: %s (%d)' % (self.video_type, video_data['label'], video_data['movieid']))
                result = exec_jsonrpc('VideoLibrary.RefreshMovie', movieid=video_data['movieid'], ignorenfo=False)
                self.log.debug(str(result))
                if (result != 'OK'):
                    self.log.warning('%s refresh failed for \'%s\' (%d)' % (self.video_type, video_data['file'], video_data['movieid']))
            except JSONRPCError as e:
                self.log.error('' + str(e))
