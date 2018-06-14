from __future__ import unicode_literals
import os.path
import xbmcvfs
from resources.lib.helpers import addon
from resources.lib.tasks import BaseTask, TaskError

class ExportTaskError(TaskError):
    pass

# base task for exporting a single video entry to nfo file
class ExportTask(BaseTask):
    JSONRPC_PROPS = [] # fields to be retrieved from library, to be overridden
    TAGS = [] # tags to be inserted in nfo, to be overridden

    def __init__(self, monitor, video_type, video_id):
        super(ExportTask, self).__init__(monitor, 'export', video_type)
        self.video_id = video_id
        # retrieve video details from the library
        self.details = self.get_details(self.video_id, properties = self.JSONRPC_PROPS)
        self.nfo_path = os.path.splitext(self.details['file'])[0] + '.nfo'

        # copy tags, in order to add some more, if needed
        self.tags = self.TAGS[:]
        # optionally include 'watched' tag
        if (addon.getSettingBool('movies.export.watched')):
            # add it to the list of tags to be built
            self.tags.append('watched')
            # also add into details, as it was not retrieved from library
            self.details['watched'] = (self.details['playcount'] > 0)
        # optionally include 'userrating' tag
        if (addon.getSettingBool('movies.export.userrating')):
            # add it to the list of tags to be built
            self.tags.append('userrating')


    # main task method, the task will get destroyed on exit
    def run(self):
        return self.export()
