from __future__ import unicode_literals
import xbmcvfs
from bs4 import BeautifulSoup
from resources.lib.helpers import addon
from resources.lib.tasks import TaskFileError
from resources.lib.tasks.export_base import ExportTask, ExportTaskError

class ExportWatchedTaskError(ExportTaskError):
    pass

class ExportWatchedTask(ExportTask):
    JSONRPC_PROPS = ['file', 'playcount', 'lastplayed', 'userrating'] # fields to be retrieved from library
    TAGS = ['playcount', 'lastplayed'] # tags to be inserted in nfo; more are added dynamically in ExportTask.__init__()

    def __init__(self, monitor, video_type, video_id):
        super(ExportWatchedTask, self).__init__(monitor, video_type, video_id)

    # update the nfo file with up-to_date information only
    def export(self):
        # TODO: manage access right issues
        try:
            soup, root = self.load_nfo(self.nfo_path, self.video_type)

            # update XML tree
            for tag_name in self.tags: # we use the copy (see __init__)
                # get the child element
                elt = root.find(tag_name)
                if (elt is None):
                    # append the element if it does not exist
                    elt = soup.new_tag(tag_name)
                    root.append(elt)
                # copy value retrieved from library into the element
                elt.string = str(self.details[tag_name])

            # write content to NFO file
            self.save_nfo(self.nfo_path, root)
        except TaskFileError as e:
            # try to regenerate the nfo file if setting is set
            if (addon.getSettingBool('movies.export.rebuild')):
                self.log.notice('%s, regenerating the whole file...' % e)
                return self.export_all()
            else:
                self.log.warning('%s, but we are not going to regenerate it (see settings)' % e)
                return False
        except Exception as e:
            self.log.error('error caught while updating nfo file: %s: %s' % (e.__class__.__name__, str(e)))
            # raise
            return False

        self.notify_result()
        return True

    # fallback to ExportAllTask, in order to regenerate the file completely
    # this requires setting 'movies.export.rebuild' to be set
    def export_all(self):
        self.log.debug('export_all()')
        from resources.lib.tasks.export_all import ExportAllTask
        self.log.notice('falling back to ExportAllTask')
        task = ExportAllTask(self.monitor, self.video_type, self.video_id)
        return task.run()
