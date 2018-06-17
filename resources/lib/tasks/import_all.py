from __future__ import unicode_literals
import xbmcvfs
from resources.lib.tasks.import_base import ImportTask, ImportTaskError
from resources.lib.helpers import timestamp_to_str, str_to_timestamp

class ImportAllTaskError(ImportTaskError):
    pass

class ImportAllTask(ImportTask):
    def __init__(self, video_type, last_import = None):
        super(ImportAllTask, self).__init__(video_type)

    # set the list of entries that should be imported again
    def scan_outdated(self):
        # we start by getting the list of all referenced videos of the given video_type
        # this is acceptable, because this task will be triggered AFTER library scans, which means that new nfo files are already integrated in the library
        # following this approach, all nfo that are not associated with an entry in the library can be gracefully ignored (they are probably falsy)
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
        nfo_path = self.get_nfo_path(video_file)

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
