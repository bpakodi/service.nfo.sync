from __future__ import unicode_literals
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

    def __init__(self, video_type, video_id):
        super(ExportTask, self).__init__('export', video_type)
        self.video_id = video_id
        # retrieve video details from the library
        self.details = self.get_details(self.video_id, properties = self.JSONRPC_PROPS)
        self.nfo_path = self.get_nfo_path(self.details['file'])
        self.title = self.details['label']

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


    @property
    def signature(self):
        return '%s export for \'%s\'' % (self.video_type, self.title)

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
        result_status = '%s complete' % self.signature # if we encounter an error, this would be used anyway, so let's be optimistic!
        result_details = ''

        try:
            # main XML processing here (method overridden by derived classes)
            (soup, root, old_raw) = self.make_xml()
        except ExportTaskXMLError as e:
            # run some last chance code if any
            return self.on_xml_failure()

        # execute external script to patch the XML structure before saving
        try:
            self.patch_xml(soup, root)
        except ExportTaskScriptError:
            result_status += ' (with script errors)'
            result_details = 'script error: see log for details'

        # write content to NFO file
        try:
            self.save_nfo(self.nfo_path, root, old_raw)
        except TaskFileError as e:
            self.log.error('error saving nfo file: \'%s\'' % e.path)
            self.log.error(str(e))
            return False

        # notify user and return successfully
        self.notify(result_status, (result_details if result_details else ''))
        return True

    # to be overridden
    # build (or patch) the xml. Returns a tuple: (soup, XML node)
    # Should raise ExportTaskXMLError on error
    def make_xml(self):
        return None

    # to be overridden
    # last chance actions before failing, return True to make this task completed successfully
    def on_xml_failure(self):
        self.notify('%s failed' % self.signature, 'error updating nfo, see log')
        return False

    # run external script to modify the XML content, if applicable
    def patch_xml(self, soup, root):
        # check in settings if we should run a script
        script_path = xbmc.translatePath(addon.getSetting('movies.export.script.path'))
        if (not addon.getSettingBool('movies.export.script') or not script_path):
            self.log.debug('not applying any script')
            return

        # executing the script
        try:
            self.exec_script_file(script_path, locals_dict = {
                'soup': soup,
                'root': root
            })
        except TaskScriptError as e:
            self.log.notice('error applying script: \'%s\'' % script_path)
            self.log.notice(str(e))
            self.log.notice('  => ignoring script error => proceeding with export anyway')
            raise ExportTaskScriptError('script error: %s' % str(e))
