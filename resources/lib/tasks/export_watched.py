from __future__ import unicode_literals
import xbmcvfs
from bs4 import BeautifulSoup
from resources.lib.helpers import addon
from resources.lib.tasks.export_base import ExportTask, ExportTaskError, ExportFileError

class ExportWatchedTaskError(ExportTaskError):
    pass

class ExportWatchedTask(ExportTask):
    JSONRPC_PROPS = ['file', 'playcount', 'lastplayed', 'userrating'] # fields to be retrieved from library
    TAGS = ['playcount', 'lastplayed'] # tags to be inserted in nfo

    def __init__(self, monitor, video_type, video_id):
        super(ExportWatchedTask, self).__init__(monitor, video_type, video_id)


    # update the nfo file with up-to_date information only
    def export(self):
        # TODO: manage access right issues
        try:
            # check if the nfo file already exists
            if (not xbmcvfs.exists(self.nfo_path)):
                raise ExportFileError('file \'%s\' does not exist' % self.nfo_path)

            # now open the file for reading, and get the content
            fp = xbmcvfs.File(self.nfo_path)
            raw = fp.read()
            fp.close()

            # load XML tree from file content
            soup = BeautifulSoup(raw, 'html.parser')
            root = soup.find(self.video_type)
            # check if the XML content is valid
            if (root is None):
                raise ExportFileError('file \'%s\' is invalid,' % self.nfo_path)

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
            self.write_nfo(soup.prettify_with_indent(encoding='utf-8'))
        except ExportFileError as e:
            # try to regenerate the nfo file if setting is set
            if (addon.getSettingBool('movies.export.rebuild')):
                self.log.notice('%s, regenerating the whole file...' % e)
                return self.export_all()
            else:
                self.log.warning('%s, but we are not going to regenerate it (see settings)' % str(e))
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
