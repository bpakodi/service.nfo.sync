from __future__ import unicode_literals
import xbmc
from resources.lib.helpers import addon
from resources.lib.tasks import BaseTask, TaskError, TaskJSONRPCError, TaskFileError, TaskScriptError
from resources.lib.nfo import NFOHandlerError
from resources.lib.nfo.movie_build import MovieNFOBuildHandler

class ExportTaskError(TaskError):
    pass
class ExportTaskJSONRPCError(ExportTaskError,TaskJSONRPCError):
    pass
class ExportTaskFileError(ExportTaskError, TaskFileError):
    pass
class ExportTaskScriptError(ExportTaskError, TaskScriptError):
    pass

# base task for exporting a single video entry to nfo file
class ExportTask(BaseTask):
    def __init__(self, video_type, ignore_script = False):
        super(ExportTask, self).__init__('export', video_type, ignore_script)

    # called when nfo content has been loaded
    def on_nfo_loaded(self, nfo, result):
        # optionally include 'watched' tag to XML content
        if (addon.getSettingBool('movies.export.watched')):
            nfo.add_tag('watched')
        # optionally include 'userrating' tag to XML content
        if (addon.getSettingBool('movies.export.userrating')):
            nfo.add_tag('userrating')

    # called when an exception was caught while processing the nfo handler
    def on_nfo_load_failed(self, nfo, result):
        # fallback to MovieNFOBuildHandler, in order to regenerate the file completely
        # first check if correct setting is activated
        if (nfo and nfo.family == 'load' and addon.getSettingBool('movies.export.rebuild')):
            self.log.warning('  => rebuilding nfo file: \'%s\'' % nfo.nfo_path)
            return MovieNFOBuildHandler('rebuild', nfo.nfo_path)
        else:
            self.log.warning('  => no fallback NFO handler => skipping video')
            return None

# task class for exporting a single video entry to nfo file
class ExportSingleTask(ExportTask):
    def __init__(self, video_type, video_id, ignore_script = False):
        super(ExportSingleTask, self).__init__(video_type, ignore_script)
        self.video_id = video_id

    # populate the list of items (video IDs) to be processed
    def populate_entries(self):
        self.log.debug('exporting entry: %d' % self.video_id)
        # we just have one item here
        self.items = [ self.video_id ]
