from __future__ import unicode_literals
import xbmcvfs
from bs4 import BeautifulSoup
from resources.lib.helpers import addon
from resources.lib.tasks import TaskScriptError, TaskFileError
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

            # execute external script to patch the XML structure before saving
            var1 = "myvar1"
            var2 = "myvar2"
            script = """
import xbmc
xbmc.log('from script :-)')
xbmc.log(repr(self))
self.log.debug('get a global - addon = %s' % addon.getAddonInfo('name'))
self.log.debug('can even use self !!!')
self.log.debug('var1 = %s' % str(var1))
self.log.debug('var2 = %s' % str(var2))
            """

            try:
                self.log.debug('executing script: %s' % 'inner code')
                self.exec_script(script, globals_dict = globals(), locals_dict = {
                  'self': self,
                  'var1': var1
                })
            except TaskScriptError as e:
                self.log.error('error executing script: \'%s\'' % e.path)
                self.log.error(str(e))
                self.log.notice(' => ignoring script error => proceeding with nfo file update anyway')

            # write content to NFO file
            self.save_nfo(self.nfo_path, root)

        except TaskFileError as e:
            self.log.error('error updating nfo file: \'%s\'' % e.path)
            self.log.error(str(e))
            # try to regenerate the nfo file if setting is set
            if (addon.getSettingBool('movies.export.rebuild')):
                self.log.notice(' => regenerating nfo file: \'%s\'' % self.nfo_path)
                return self.export_all()
            else:
                self.log.warning(' => aborting nfo file update: \'%s\'' % self.nfo_path)
                self.notify('%s export failed', 'error updating nfo, see log', True)
                return False
        except Exception as e:
            self.log.error('error updating nfo file: \'%s\': %s: %s' % (self.nfo_path, e.__class__.__name__, str(e)))
            # raise
            self.notify('%s export failed', 'error updating nfo, see log', True)
            return False

        self.notify('%s export complete' % self.video_type, notify_user = True)
        return True

    # fallback to ExportAllTask, in order to regenerate the file completely
    # this requires setting 'movies.export.rebuild' to be set
    def export_all(self):
        self.log.debug('export_all()')
        from resources.lib.tasks.export_all import ExportAllTask
        self.log.notice('falling back to ExportAllTask')
        task = ExportAllTask(self.monitor, self.video_type, self.video_id)
        return task.run()
