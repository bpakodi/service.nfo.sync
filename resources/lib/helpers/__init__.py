from __future__ import unicode_literals
from datetime import datetime
import os.path
import re
from bs4 import BeautifulSoup, Tag
import xbmc
import xbmcaddon
import xbmcvfs

### addon shortcuts
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_id = addon.getAddonInfo('id')
addon_profile = xbmc.translatePath(addon.getAddonInfo('profile')).decode("utf-8")


##############################
### base exception classes ###
##############################
class Error(Exception):
    def __init__(self, message, ex = None):
        super(Error, self).__init__(message)
        self.message = message
        self.ex = ex

    # typically used to log exception messages
    def dump(self, log_fct, details_prefix = '  >> '):
        if (log_fct and self.ex):
            log_fct(details_prefix + '%s: %s' % (self.ex.__class__.__name__, self.ex))

######################
### helper methods ###
######################
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

def plural(word, value):
    return '%d %s%s' % (value, word, 's' if (value > 1) else '')

##########################################################
### helper methods: load / save to addon data location ###
##########################################################
# base class for task exceptions raised while loading / saving
class FileError(Error):
    def __init__(self, path, err_msg, ex = None):
        self.path = path
        self.err_msg = err_msg
        self.ex = ex
    def __str__(self):
        if (self.ex):
            return '%s: %s: %s' % (self.err_msg, self.ex.__class__.__name__, str(self.ex))
        else:
            return '%s' % self.err_msg

# get the nfo file path, given the video one
def get_nfo_path(video_path):
    return os.path.splitext(video_path)[0] + '.nfo'

# load data from file
def load_file(path, dir = ''):
    full_path = os.path.join(dir, path) if dir else path
    # check if the file already exists
    if (not xbmcvfs.exists(full_path)):
        raise FileError(full_path, 'file does not exist')
    # open and read from it
    try:
        fp = xbmcvfs.File(full_path)
        data = fp.read()
        fp.close()
        return data.decode('utf-8')
    except Exception as e:
        raise FileError(path, 'cannot load file', e)
# save data to file
def save_file(path, data, dir = ''):
    full_path = os.path.join(dir, path) if dir else path
    # xbmcvfs will not truncate the file, if content is smaller than previously, so let's delete the file first
    xbmcvfs.delete(full_path)
    try:
        fp = xbmcvfs.File(full_path, 'w')
        result = fp.write(data.encode('utf-8'))
        fp.close()
    except Exception as e:
        raise FileError(path, 'cannot save file', e)

    # it seems xbmcvfs does not raise any exception at all...
    if (not result):
        raise FileError(path, 'cannot save file: unknown error')
# load data from data file
def load_data(path):
    return load_file(path, dir = addon_profile)
# save data to data file
def save_data(path, data):
    save_file(path, data, dir = addon_profile)
# load soup from nfo file (XML)
def load_nfo(nfo_path, root_tag):
    # load raw data from file (may throw exceptions)
    raw = load_file(nfo_path) # already contains the full path
    # load XML tree from file content
    try:
        soup = BeautifulSoup(raw, 'html.parser')
        root = soup.find(root_tag)
    except Exception as e:
        raise FileError(nfo_path, 'invalid nfo file: not a valid XML document', e)

    # check if the XML content is valid
    if (root is None):
        raise FileError(nfo_path, 'invalid nfo file: no root tag \'%s\'' % root_tag)
    # everything is OK, return
    return (soup, root, raw)

# save soup tag to nfo file (XML)
# if old_raw is set, perform a check, and do not save if identical
# True if content was actually saved, False if save was skipped
def save_nfo(nfo_path, root, old_raw = None):
    # generate content
    content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    content = content + root.prettify_with_indent()

    # only save if content has been updated
    # to perform that, we just compare string outputs. Dirty but acceptable, because strictly speaking XML is order-sensitive...
    if (old_raw and old_raw == content):
        return False

    try:
        save_file(nfo_path, content)
        return True
    except FileError:
        raise
    except Exception as e:
        raise FileError(nfo_path, 'cannot save nfo file', e)

##########################################################
### Monkey-patch BeautifulSoup with nicer pretty print ###
##########################################################
# see https://stackoverflow.com/questions/47879140/how-to-prettify-html-so-tag-attributes-will-remain-in-one-single-line
# and https://code.i-harness.com/en/q/b70e4

def prettify_with_indent(self, indent_width = 4, single_lines = True, encoding=None, formatter='minimal'):
    # # compact attrs
    # if single_lines:
    #     for tag in self():
    #         for attr in tag.attrs:
    #             # print(tag.attrs[attr], tag.attrs[attr].__class__)
    #             tag.attrs[attr] = " ".join(
    #                 tag.attrs[attr].replace("\n", " ").split())
    # get prettify() before applying modifications
    output = self.prettify(encoding, formatter)
    # compact nodes
    if single_lines:
        r = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
        output = r.sub('>\g<1></', output)

    # set indentation
    r = re.compile(r'^(\s*)', re.MULTILINE)
    return r.sub(r'\1' * indent_width, output)

BeautifulSoup.prettify_with_indent = prettify_with_indent
Tag.prettify_with_indent = prettify_with_indent
