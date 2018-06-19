from __future__ import unicode_literals
import xbmc
from resources.lib.helpers import addon
from resources.lib.helpers.log import log
from resources.lib.monitor import NFOMonitor

if __name__ == '__main__':

    if (addon.getSettingInt('debug.nb_threads') == 0):
        log.fatal('no thread at all??? Are you serious??? I cannot work this way, I quit')
        exit()

    monitor = NFOMonitor(nb_threads = addon.getSettingInt('debug.nb_threads'))

    log.notice('service started')

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort():
            # Abort was requested while waiting. We should exit
            break

    log.notice('stopping service')
    monitor.stop_all_threads()
    log.notice('service stopped')
