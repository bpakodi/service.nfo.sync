from __future__ import unicode_literals
import xbmc
from resources.lib.helpers import addon_id, Error

# see https://forum.kodi.tv/showthread.php?tid=144677
# log admits both unicode strings and str encoded with "utf-8" (or ascii). will fail with other str encodings.
def _log(msg, level = xbmc.LOGDEBUG):
    if isinstance(msg, str):
        msg = msg.decode('utf-8')  # if it is str we assume it's "utf-8" encoded.
                                   # will fail if called with other encodings (latin, etc) BE ADVISED!
    # at this point we are sure msg is a unicode string.
    message = u'%s: %s' % (addon_id, msg)
    xbmc.log(message.encode("utf-8"), level)

class Logger(object):
    def __init__(self, ns = None):
        if (ns):
            self.prefix = ns + ' > '
        else:
            self.prefix = ''

    def log(self, msg, level = xbmc.LOGDEBUG):
        if (isinstance(msg, Error)):
            _log(self.prefix + str(msg) + ':', level)
            if (msg.ex):
                _log(self.prefix + '  >> ' + '%s: %s' % (msg.ex.__class__.__name__, str(msg.ex)), level)
        elif (isinstance(msg, Exception)):
            _log(self.prefix + str(msg), level)
        else:
            _log(self.prefix + msg, level)

    def debug(self, msg):
        self.log(msg, xbmc.LOGDEBUG)
    def info(self, msg):
        self.log(msg, xbmc.LOGINFO)
    def notice(self, msg):
        self.log(msg, xbmc.LOGNOTICE)
    def warning(self, msg):
        self.log(msg, xbmc.LOGWARNING)
    def error(self, msg):
        self.log(msg, xbmc.LOGERROR)
    def fatal(self, msg):
        self.log(msg, xbmc.LOGFATAL)

log = Logger() # default logger without prefix
