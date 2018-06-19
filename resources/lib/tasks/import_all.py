from __future__ import unicode_literals
import xbmcvfs
from resources.lib.tasks import TaskJSONRPCError
from resources.lib.tasks.import_base import ImportTask, ImportTaskError
from resources.lib.helpers import timestamp_to_str, str_to_timestamp, get_nfo_path
import resources.lib.library as Library
LibraryError = Library.LibraryError # just as a convenience

class ImportAllTaskError(ImportTaskError):
    pass

class ImportAllTask(ImportTask):
    def __init__(self, video_type, ignore_script = False, last_import = None):
        super(ImportAllTask, self).__init__(video_type, ignore_script, last_import)

    # populate the list of entries (video details) to be processed
    def populate_entries(self):
        # we start by getting the list of all referenced videos of the given video_type
        # this is acceptable, because this task will be triggered AFTER library scans, which means that new nfo files are already integrated in the library
        # following this approach, all nfo that are not associated with an entry in the library can be gracefully ignored (they are probably falsy)
        self.log.debug('scanning library for nfo files newer than %s' % timestamp_to_str(self.last_import))
        # retrieve all video entries in the library
        self.items = []
        try:
            entries = Library.get_list(self.video_type, properties = ['file']) # may raise TaskJSONRPCError
        except LibraryError as e:
            raise TaskJSONRPCError('error retrieving the list of %ss' % self.video_type, e.ex)

        for entry in entries:
            # check the modification timestamp of each nfo file
            if (self.inspect_nfo(entry['file'])):
                self.items.append(entry[self.video_type + 'id'])

    # inspect a nfo file to check if the corresponding video library entry should be refreshed
    def inspect_nfo(self, video_file):
        # build .nfo file name from the video one
        nfo_path = get_nfo_path(video_file)

        if (not xbmcvfs.exists(nfo_path)):
            return
        # get the last modified timestamp
        stat = xbmcvfs.Stat(nfo_path)
        last_modified = stat.st_mtime()
        # check if the nfo file was modified after last_import
        return (last_modified > self.last_import)
