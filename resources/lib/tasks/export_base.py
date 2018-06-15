from __future__ import unicode_literals
import os.path
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
            root = self.make_xml()
        except ExportTaskXMLError:
            # run some last chance code if any
            return self.on_xml_failure()

        # execute external script to patch the XML structure before saving
        try:
            self.apply_script(root)
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
    # build (or patch) the xml. Returns a XML node
    # Should raise ExportTaskXMLError on error
    def make_xml(self):
        return None

    # to be overridden
    # last chance actions before failing, return True to make this task completed successfully
    def on_xml_failure(self):
        self.notify('%s failed' % self.task_label, '%s\nerror updating nfo, see log' % self.video_title, True)
        return False

    # run external script to modify the XML content, if applicable
    def apply_script(self, root):
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
              'root': root,
              'var1': var1
            })
        except (TaskScriptError, TaskFileError) as e:
            self.log.error('error executing script: \'%s\'' % e.path)
            self.log.error(str(e))
            self.log.notice('  => ignoring script error => proceeding with nfo file update anyway')
            raise ExportTaskScriptError('script error: %s' % str(e))
