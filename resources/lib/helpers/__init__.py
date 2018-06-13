from __future__ import unicode_literals
from datetime import datetime
import xbmc
import xbmcaddon

### addon shortcuts
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_id = addon.getAddonInfo('id')
addon_profile = xbmc.translatePath(addon.getAddonInfo('profile')).decode("utf-8")

def timestamp_to_str(timestamp):
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # return gracefully
        return ''

def str_to_timestamp(date_string):
    # workaround for known bug
    # see https://bugs.python.org/issue27400
    # see https://forum.kodi.tv/showthread.php?tid=112916
    import time
    try:
        try:
            return time.mktime(datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S'))
        except TypeError:
            # return datetime(*(time.strptime(date_string, '%Y-%m-%d %H:%M:%S')[0:6]))
            return time.mktime(time.strptime(date_string, '%Y-%m-%d %H:%M:%S'))
            # return time.mktime(datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').date().timetuple())
    except ValueError:
        # return gracefully if string is not valid
        return 0
