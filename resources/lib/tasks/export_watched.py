from __future__ import unicode_literals
import xbmcvfs
from bs4 import BeautifulSoup
from resources.lib.helpers import addon
from resources.lib.tasks import TaskScriptError, TaskFileError
from resources.lib.tasks.export_base import ExportTask, ExportTaskError, ExportTaskXMLError

class ExportWatchedTaskError(ExportTaskError):
    pass

class ExportWatchedTask(ExportTask):
    JSONRPC_PROPS = ['file', 'playcount', 'lastplayed', 'userrating'] # fields to be retrieved from library
    TAGS = ['playcount', 'lastplayed'] # tags to be inserted in nfo; more are added dynamically in ExportTask.__init__()

    def __init__(self, video_type, video_id):
        super(ExportWatchedTask, self).__init__(video_type, video_id)

    # update the nfo file with up-to_date information only
    def make_xml(self):
        try:
            # load soup from file
            (soup, root, old_raw) = self.load_nfo(self.nfo_path, self.video_type)
            # update XML tree
            for tag_name in self.tags:
                # get the child element
                elt = root.find(tag_name)
                if (elt is None):
                    # append the element if it does not exist
                    elt = soup.new_tag(tag_name)
                    root.append(elt)
                # copy value retrieved from library into the element
                elt.string = str(self.details[tag_name])
            # return root node
            return (soup, root, old_raw)
        except (TaskFileError, Exception) as e:
            self.log.error('error loading nfo file: \'%s\'' % self.nfo_path)
            self.log.error(str(e))
            raise ExportTaskXMLError('error loading nfo file: \'%s\'' % self.nfo_path)

    def on_xml_failure(self):
        # fallback to ExportAllTask, in order to regenerate the file completely
        # first check if correct setting is activated
        if (addon.getSettingBool('movies.export.rebuild')):
            self.log.notice('  => regenerating nfo file: \'%s\'' % self.nfo_path)
            # instance a ExportAllTask object, and directly execute its run() method
            from resources.lib.tasks.export_all import ExportAllTask
            self.log.notice('falling back to ExportAllTask')
            task = ExportAllTask(self.video_type, self.video_id)
            return task.run()
        else:
            self.log.warning('  => aborting nfo file update: \'%s\'' % self.nfo_path)
            self.notify('%s failed' % self.signature, 'error updating nfo, see log')
            return False
