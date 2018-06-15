from __future__ import unicode_literals
import os.path
import xbmc
import xbmcvfs
from resources.lib.helpers import addon
from resources.lib.tasks import BaseTask, TaskError, TaskFileError, TaskScriptError

class ExportTaskError(TaskError):
    pass
class ExportTaskXMLError(TaskError):
    pass
class ExportTaskScriptError(TaskError):
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


    # override to customize logs
    @property
    def task_label(self):
        return '%s export' % self.video_type
    # useful for notifications and so
    @property
    def video_title(self):
        try:
            return self.details['label']
        except:
            return ''

    # main task method, the task will get destroyed on exit
    def run(self):
        # define some notification / log text
        result_status = '%s complete' % self.task_label # if we encounter an error, this would be used anyway, so let's be optimistic!
        result_details = ''

        try:
            # main XML processing here (method overridden by derived classes)
            (soup, root) = self.make_xml()
        except ExportTaskXMLError as e:
            # run some last chance code if any
            return self.on_xml_failure()

        # execute external script to patch the XML structure before saving
        try:
            self.apply_script(soup, root)
        except ExportTaskScriptError:
            result_status += ' (with script errors)'
            result_details = 'script error: see log for details'

        try:
            # write content to NFO file
            self.save_nfo(self.nfo_path, root)
        except TaskFileError as e:
            self.log.error('error saving nfo file: \'%s\'' % e.path)
            self.log.error(str(e))
            return False

        # notify user and return successfully
        self.notify(result_status, '%s%s' % (self.video_title, ('\n' + result_details if result_details else '')), True)
        return True

    # to be overridden
    # build (or patch) the xml. Returns a tuple: (soup, XML node)
    # Should raise ExportTaskXMLError on error
    def make_xml(self):
        return None

    # to be overridden
    # last chance actions before failing, return True to make this task completed successfully
    def on_xml_failure(self):
        self.notify('%s failed' % self.task_label, '%s\nerror updating nfo, see log' % self.video_title, True)
        return False

    # run external script to modify the XML content, if applicable
    def apply_script(self, soup, root):
        var1 = "myvar1"
        var2 = "myvar2"

        script_path = xbmc.translatePath(addon.getSetting('movies.export.script.path'))
        if (not addon.getSettingBool('movies.export.script') or not script_path):
            self.log.debug('not applying any script')
            return

        # executing the script
        try:
            self.log.debug('executing script: %s' % script_path)
            self.exec_script(soup, root, script_path, locals_dict = {
              'var1': var1
            })
            self.log.debug('script executed: %s' % script_path)
        except TaskScriptError as e:
            self.log.notice('  => ignoring script error => proceeding with nfo file update anyway')
            raise ExportTaskScriptError('script error: %s' % str(e))
