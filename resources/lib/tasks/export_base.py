from __future__ import unicode_literals
import xbmc
from resources.lib.helpers import addon, save_nfo
from resources.lib.tasks import BaseTask, TaskError, TaskFileError, TaskScriptError
from resources.lib.tasks.export_strategies import UpdateExportStrategy, RebuildExportStrategy, ExportStrategyError

class ExportTaskError(TaskError):
    pass
class ExportTaskXMLError(TaskError):
    pass
class ExportTaskScriptError(TaskError):
    pass
class ExportTaskStrategyError(TaskError):
    pass

# base task for exporting a single video entry to nfo file
class ExportTask(BaseTask):
    STRATEGIES = {
        'update': UpdateExportStrategy,
        'rebuild': RebuildExportStrategy,
    }

    def __init__(self, video_type, video_id, strategy = 'update'):
        super(ExportTask, self).__init__('export', video_type)
        self.video_id = video_id
        self.default_strategy = strategy

    # useful for notifications and so
    @property
    def video_title(self):
        try:
            return self.video_details['label']
        except:
            return ''

    # main task method, the task will get destroyed on exit
    def run(self):
        # first instanciate the default strategy; if it fails, try to fallback to another one
        strategy = self.make_strategy(self.default_strategy, self.video_id)
        while (strategy):
            try:
                # patch or build the XML content, using strategy.make_xml()
                self.log.notice('applying export strategy \'%s\'' % strategy.type)
                strategy.make_xml()
                break
            except ExportStrategyError as e:
                self.log.error(unicode(e))
                self.log.error('Error was: %s: %s' % (e.__class__.__name__, str(e.ex)))
                # strategy failed, try to fallback to another one
                strategy = self.on_strategy_failure(strategy)
                # new strategy may be None => break
        # strategy failed and we got no fallback
        if (not strategy):
            return False

        # define some notification / log text, than can be modified later on
        result_status = '%s export for \'%s\' complete' % (self.video_type, strategy.video_title) # if we encounter an error, this would be used anyway, so let's be optimistic!
        result_details = ''

        # execute external script to patch the XML structure before saving
        try:
            self.patch_xml(strategy)
        except ExportTaskScriptError:
            result_status += ' (with script errors)'
            result_details = 'script error: see log for details'

        # write content to NFO file
        try:
            if (save_nfo(strategy.nfo_path, strategy.root, strategy.old_raw)):
                self.log.debug('nfo saved to \'%s\'' % strategy.nfo_path)
            else:
                self.log.debug('not saving to \'%s\': contents are identical' % strategy.nfo_path)
        except TaskFileError as e:
            self.log.error('error saving nfo file: \'%s\'' % strategy.nfo_path)
            self.log.error('Error was: %s' % str(e))
            return False

        # notify user and return successfully
        self.notify(result_status, (result_details if result_details else ''))
        return True

    # initialize the given strategy
    def make_strategy(self, strategy_type, video_id):
        # get the ExportStrategy derived class
        try:
            strategy_klass = self.STRATEGIES[strategy_type]
        except KeyError:
            self.log.error('unknown strategy \'%s\'' % str(strategy_type))
            return None

        # retrieve video details from the library
        # the list of needed props is provided by the strategy itself
        video_details = self.get_details(self.video_id, properties = strategy_klass.JSONRPC_PROPS)

        # build the list of tags we need to generate (and possibly modify video_details), based on those provided by the strategy
        export_tags = strategy_klass.EXPORT_TAGS[:]
        # optionally include 'watched' tag
        if (addon.getSettingBool('movies.export.watched')):
            # add it to the list of tags to be built
            export_tags.append('watched')
            # also add into details, as it was not retrieved from library
            video_details['watched'] = (video_details['playcount'] > 0)
        # optionally include 'userrating' tag
        if (addon.getSettingBool('movies.export.userrating')):
            # add it to the list of tags to be built
            export_tags.append('userrating')

        # return newly instanciated strategy object
        return strategy_klass(self, strategy_type, self.video_type, video_id, video_details, export_tags)

    # fallback actions before failing
    # returns a new strategy object if applicable
    def on_strategy_failure(self, strategy):
        # fallback to RebuildExportStrategy, in order to regenerate the file completely
        # first check if correct setting is activated
        if (strategy.type == 'update' and addon.getSettingBool('movies.export.rebuild')):
            self.log.notice('  => rebuilding nfo file: \'%s\'' % strategy.nfo_path)
            # instance a ExportAllTask object, and directly execute its run() method
            return self.make_strategy('rebuild', strategy.nfo_path)
        else:
            self.log.warning('  => aborting nfo file update: \'%s\'' % strategy.nfo_path)
            self.notify('%s export for \'%s\' failed' % (self.video_type, strategy.video_title), 'error updating nfo, see log')
            return False

    # run external script to modify the XML content, if applicable
    def patch_xml(self, strategy):
        # check in settings if we should run a script
        script_path = xbmc.translatePath(addon.getSetting('movies.general.script.path'))
        if (not addon.getSettingBool('movies.general.script') or not script_path):
            self.log.debug('not applying any script')
            return

        # executing the script
        try:
            self.exec_script_file(script_path, locals_dict = {
                'soup': strategy.soup,
                'root': strategy.root,
                'nfo_path': strategy.nfo_path,
                'video_path': strategy.video_path,
                'video_type': strategy.video_type,
                'video_title': strategy.video_title,
                'task_family': self.task_family,
            })
        except TaskScriptError as e:
            self.log.notice('error applying script: \'%s\'' % script_path)
            self.log.notice(str(e))
            self.log.notice('  => ignoring script error => proceeding with export anyway')
            raise ExportTaskScriptError('script error: %s' % str(e))
