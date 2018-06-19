from __future__ import unicode_literals
import xbmcvfs

from resources.lib.tasks.import_base import ImportTask, ImportTaskError

class ImportSingleTaskError(ImportTaskError):
    pass

class ImportSingleTask(ImportTask):
    def __init__(self, video_type, video_id, ignore_script = False, last_import = None):
        super(ImportSingleTask, self).__init__(video_type, ignore_script, last_import)
        if (not video_id):
            raise ImportSingleTaskError('empty %s ID' % self.video_type)
        self.video_id = video_id
        self.save_resume_point = False # don't save resume point for a single entry

    # populate the list of items (video IDs) to be processed
    def populate_entries(self):
        self.log.debug('importing single entry: %d' % self.video_id)
        # we just have one item here
        self.items = [ self.video_id ]
