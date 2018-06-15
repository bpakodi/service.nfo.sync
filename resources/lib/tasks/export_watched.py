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

    def __init__(self, monitor, video_type, video_id):
        super(ExportWatchedTask, self).__init__(monitor, video_type, video_id)

    # update the nfo file with up-to_date information only
    def export_old(self):
        return self.export_all()
        # TODO: manage access right issues
        try:
            result_msg = '%s export complete' # will not be used otherwise, so let's be optimistic!
            result_details = ''
            # load soup from file
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
log.debug('can even log from there!')
log.debug('var1 = %s' % str(var1))
log.debug('var2 = %s' % str(var2))
log.debug('this is the end, my friend')
            """

            try:
                self.log.debug('executing script: %s' % 'inner code')
                self.exec_script(script, globals_dict = globals(), locals_dict = {
                  'log': self.log,
                  'var1': var1
                })
            except (TaskScriptError, TaskFileError) as e:
                result_msg += ' (with script error)'
                result_details = 'script error: see log for details'
                self.log.error('error executing script: \'%s\'' % e.path)
                self.log.error(str(e))
                self.log.notice('  => ignoring script error => proceeding with nfo file update anyway')

            # write content to NFO file
            self.save_nfo(self.nfo_path, root)

            # notify user and return successfully
            self.notify(result_msg, result_details, True)
            return True

        except TaskFileError as e:
            self.log.error('error updating nfo file: \'%s\'' % e.path)
            self.log.error(str(e))
            # try to regenerate the nfo file if setting is set
            if (addon.getSettingBool('movies.export.rebuild')):
                self.log.notice('  => regenerating nfo file: \'%s\'' % self.nfo_path)
                return self.export_all()
            else:
                self.log.warning('  => aborting nfo file update: \'%s\'' % self.nfo_path)
                self.notify('%s export failed', 'error updating nfo, see log', True)
                return False
        except Exception as e:
            self.log.error('error updating nfo file: \'%s\': %s: %s' % (self.nfo_path, e.__class__.__name__, str(e)))
            # raise
            self.notify('%s export failed', 'error updating nfo, see log', True)
            return False

    # update the nfo file with up-to_date information only
    def make_xml(self):
        try:
            # load soup from file
            soup, root = self.load_nfo(self.nfo_path, self.video_type)
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
            return root
        except (TaskFileError, Exception) as e:
            self.log.error('error loading nfo file: \'%s\'' % e.path)
            self.log.error(str(e))
            raise ExportTaskXMLError('error loading nfo file: \'%s\'' % e.path)

    def on_xml_failure(self):
        # fallback to ExportAllTask, in order to regenerate the file completely
        # first check if correct setting is activated
        if (addon.getSettingBool('movies.export.rebuild')):
            self.log.notice('  => regenerating nfo file: \'%s\'' % self.nfo_path)
            # instance a ExportAllTask object, and directly execute its run() method
            from resources.lib.tasks.export_all import ExportAllTask
            self.log.notice('falling back to ExportAllTask')
            task = ExportAllTask(self.monitor, self.video_type, self.video_id)
            return task.run()
        else:
            self.log.warning('  => aborting nfo file update: \'%s\'' % self.nfo_path)
            self.notify('%s failed' % self.task_label, '%s\nerror updating nfo, see log' % self.video_title, True)
            return False
