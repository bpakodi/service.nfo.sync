from __future__ import unicode_literals
import xbmc
import xbmcgui
import json
from resources.lib.helpers import addon
from resources.lib.helpers.log import Logger
from resources.lib.helpers.jsonrpc import exec_jsonrpc, JSONRPCError

from Queue import Queue
from resources.lib.tasks import Thread

# import various tasks
from resources.lib.tasks.import_all import ImportAllTask
from resources.lib.tasks.export_base import ExportTask

class NFOMonitor(xbmc.Monitor):
    def __init__(self, nb_threads = 2):
        super(NFOMonitor, self).__init__()
        # init custom logging
        self.log = Logger(self.__class__.__name__)

        # init multithreading
        self.log.info('initializing multithreading with %d threads' % nb_threads)
        self.tasks = Queue() # task queue
        self.threads = [] # thread list
        for i in range(nb_threads):
            # start as many threads as requested and add them to the list
            w = Thread(self.tasks)
            # w.daemon = True
            # add new thread to the list of threads
            self.threads.append(w)
            w.start()

    def stop_all_threads(self):
        self.log.info('aborting monitor worker threads')
        self.tasks.join()
        for w in self.threads:
            w.stop()
        self.log.info('all monitor worker threads have been stopped')

    def add_task(self, task):
        self.tasks.put(task)

    def onNotification(self, sender, method, data):
        # self.log.debug('notification received: %s' % method)
        data_dict = json.loads(data)
        if (method == 'VideoLibrary.OnScanFinished'):
            self.log.info('library scan finished => launching ImportAllTask')
            self.add_task(ImportAllTask('movie'))
        elif (method == 'VideoLibrary.OnUpdate' and 'playcount' in data):
            # perform additional checks
            try:
                if (data_dict['item']['type'] != 'movie' or not data_dict['item']['id']):
                    raise KeyError('invalid video type or id, ignoring')
            except KeyError:
                # gracefully return
                return
            self.log.info('watched status updated => launching ExportTask for %s #%d' % (data_dict['item']['type'], data_dict['item']['id']))
            self.add_task(ExportTask(data_dict['item']['type'], data_dict['item']['id']))
