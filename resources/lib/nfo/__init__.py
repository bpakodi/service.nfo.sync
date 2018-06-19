from __future__ import unicode_literals
from bs4 import BeautifulSoup, Tag
from resources.lib.helpers import Error
from resources.lib.helpers import get_nfo_path, load_nfo, save_nfo, FileError
import resources.lib.library as Library
LibraryError = Library.LibraryError # just as a convenience

class NFOHandlerError(Error):
    def __init__(self, message, nfo = None, ex = None):
        super(NFOHandlerError, self).__init__(message, ex)
        self.nfo = nfo

# base class for managing I/O with a NFO file
# the handler is given video_details in args, and is responsible for instantiating soup related vars
# basically it holds soup, root, and old_raw members, as well as all details about the video
class NFOHandler(object):
    JSONRPC_PROPS = ['file', 'playcount', 'userrating'] # fields to get from library

    def __init__(self, task, video_type, video_id, family = 'load'):
        self.family = family
        self.task = task
        self.video_type = video_type
        self.video_id = video_id
        self.modified = False
        # retrieve details about the entry from the library
        # the list of needed props is provided by the handler itself
        try:
            self.entry = Library.get_details(self.video_type, self.video_id, properties = self.JSONRPC_PROPS)
        except LibraryError as e:
            raise NFOHandlerError('error retrieving video details from library', ex = e.ex)
        # simulate a watched prop in lib entry, that can be useful in derived classes
        self.entry['watched'] = (self.entry['playcount'] > 0)
        # set some useful vars
        self.video_path = self.entry['file']
        self.nfo_path = get_nfo_path(self.video_path)
        self.video_title = self.entry['label']

    # to be overridden
    # initialize the soup, root, old_raw members
    def make_xml(self):
        pass

    # load XML content from file
    def load(self):
        try:
            (self.soup, self.root, self.old_raw) = load_nfo(self.nfo_path, self.video_type)
        except FileError as e:
            raise NFOHandlerError('error loading nfo file', self.nfo_path, e)

    # save XML content to nfo file, only if XML content is different from the initial one
    # returns True if there was no error, AND the content was actually saved
    def save(self):
        try:
            self.modified = save_nfo(self.nfo_path, self.root, self.old_raw)
            return self.modified
        except FileError as e:
            raise NFOHandlerError('error saving nfo file', self.nfo_path, e)

    # append a tag to root node
    # value may be either a string, a Tag to be inserted inside the new element, or None
    # if None, value will be retrieved from the entry details
    def add_tag(self, tag_name, value = None, parent = None, replace = False):
        # get default value from details if needed
        if (not value):
            try:
                value = self.entry[tag_name]
            except KeyError:
                raise NFOHandlerError('cannot add tag \'%s\': no default value in video details' % tag_name, self.nfo_path)
        # by default, appending to root node
        if (not parent):
            parent = self.root
        # update the XML tree
        try:
            # optionally remove all tags with same name
            if (replace):
                self.del_tags(tag_name, parent = parent)
            # append the element to root
            elt = self.soup.new_tag(tag_name)
            parent.append(elt)
            # set element content
            if (isinstance(value, Tag)):
                elt.append(value)
            else:
                elt.string = str(value)
            return elt
        except NFOHandlerError:
            raise
        except Exception as e:
            raise NFOHandlerError('error updating the XML content (add)', self.nfo_path, e)

    # append a tag to root node
    # value may be either a string, a Tag to be inserted inside the new element, or None
    # if None, value will be retrieved from the entry details
    def del_tags(self, tag_name, parent = None):
        # get default value from details if needed
        # by default, appending to root node
        if (not parent):
            parent = self.root
        # update the XML tree
        try:
            for elt in parent.find_all(tag_name, recursive = False):
                elt.decompose()
        except Exception as e:
            raise NFOHandlerError('error updating the XML content (del)', self.nfo_path, e)


# load content from file
class NFOLoadHandler(NFOHandler):
    # initialize the soup, root, old_raw members
    def make_xml(self):
        # by default, load content from file
        self.load()


# build the NFO from scratch
# "virtual" class, to be derived for each video type
class NFOBuildHandler(NFOHandler):
    # JSONRPC_PROPS and TAGS to be set in derived classes
    TAGS = [] # tags to generate; they will be processed sequentially in make_xml()

    def __init__(self, task, video_type, video_id):
        super(NFOBuildHandler, self).__init__(task, video_type, video_id, family = 'build')

    # initialize the soup, root, old_raw members
    def make_xml(self):
        # build new XML content
        self.soup = BeautifulSoup('', 'html.parser')
        self.root = self.soup.new_tag(self.video_type)
        self.soup.append(self.root)

        # append child nodes
        try:
            for tag_name in self.TAGS:
                self.build_tag(tag_name)
        except Exception as e:
            raise NFOHandlerError('error building the NFO', self.nfo_path, e)

    # to be overridden
    # called from loop in make_xml()
    def build_tag(self, tag_name):
        self.add_tag(tag_name)
