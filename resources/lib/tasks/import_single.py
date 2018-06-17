from __future__ import unicode_literals
import xbmcvfs
from resources.lib.tasks import TaskJSONRPCError
from resources.lib.tasks.import_base import ImportTask, ImportTaskError
from resources.lib.helpers import timestamp_to_str, str_to_timestamp

class ImportSingleTaskError(ImportTaskError):
    pass

class ImportSingleTask(ImportTask):
    def __init__(self, video_type, video_id, last_import = None):
        super(ImportSingleTask, self).__init__(video_type)
        if (not video_id):
            raise ImportSingleTaskError('empty %s ID' % self.video_type)
        self.video_id = video_id

    # set the list of entries that should be imported again
    def scan_outdated(self):
        self.log.debug('importing entry: %d' % self.video_id)
        # retrieve details of the given video entry, and add them to self.outdated
        try:
            video_details = self.get_details(self.video_id, properties = ['file'])
            self.outdated.append(video_details)
        except TaskJSONRPCError as e:
            self.log.error('invalid %s ID \'%s\'' % (self.video_type, str(self.video_id))
            self.log.error('Error was: %s' % str(e))
            raise ImportSingleTaskError('invalid %s ID \'%s\'' % (self.video_type, str(self.video_id))
