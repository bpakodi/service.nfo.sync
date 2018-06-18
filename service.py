from __future__ import unicode_literals
import xbmc
from resources.lib.helpers.log import log
from resources.lib.monitor import NFOMonitor

if __name__ == '__main__':
    monitor = NFOMonitor()

    log.notice('service started')

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort():
            # Abort was requested while waiting. We should exit
            break

    log.notice('stopping service')
    monitor.stop_all_threads()
    log.notice('service stopped')
