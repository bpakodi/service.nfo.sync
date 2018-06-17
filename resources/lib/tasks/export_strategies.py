from __future__ import unicode_literals
from bs4 import BeautifulSoup
from resources.lib.helpers import get_nfo_path, load_nfo, FileError
from resources.lib.tasks import TaskError

class ExportStrategyError(TaskError):
    def __init__(self, nfo_path, err_msg, ex = None):
        self.nfo_path = nfo_path
        self.err_msg = err_msg
        self.ex = ex
    def __str__(self):
        return u'%s: %s' % (self.err_msg, self.nfo_path)

# base class for export strategies, implementing the make_xml() method
# they will build or patch XML content linked to a single video entry
# basically they hold soup, root, and old_raw members, as well as all details about the video
class ExportStrategy(object):
    JSONRPC_PROPS = ['file'] # fields to be retrieved from library
    EXPORT_TAGS = [] # tags to be inserted in nfo; more are added dynamically in ExportTask.__init__()

    def __init__(self, task, strategy_type, video_type, video_id, video_details, export_tags):
        self.task = task
        self.type = strategy_type
        self.video_type = video_type
        self.video_id = video_id
        self.video_details = video_details
        self.export_tags = export_tags
        self.video_path = self.video_details['file']
        self.nfo_path = get_nfo_path(self.video_path)
        self.video_title = self.video_details['label']
        # following will be set by make_xml()
        self.soup = None
        self.root = None
        self.old_raw = ''

    # to be overridden
    # build the XML / soup object
    # returns (soup, root, old_raw)
    def make_xml(self):
        pass

# update the nfo file with up-to_date information only
class UpdateExportStrategy(ExportStrategy):
    JSONRPC_PROPS = ['file', 'playcount', 'lastplayed', 'userrating'] # fields to be retrieved from library
    EXPORT_TAGS = ['playcount', 'lastplayed'] # tags to be inserted in nfo; more are added dynamically in ExportTask.__init__()

    # load the existing nfo, and modify exported tags only
    def make_xml(self):
        # load soup from file
        try:
            (soup, root, old_raw) = load_nfo(self.nfo_path, self.video_type)
        except FileError as e:
            raise ExportStrategyError(self.nfo_path, 'failed updating nfo: error loading file: %s' % e.err_msg, e)

        # update XML tree
        try:
            for tag_name in self.export_tags:
                # get the child element
                elt = root.find(tag_name)
                if (elt is None):
                    # append the element if it does not exist
                    elt = soup.new_tag(tag_name)
                    root.append(elt)
                # copy value retrieved from library into the element
                elt.string = str(self.video_details[tag_name])
            # return root node
            self.soup = soup
            self.root = root
            self.old_raw = old_raw
        except Exception as e:
            raise ExportStrategyError(self.nfo_path, 'failed updating nfo: error patching content', e)

# build a brand new nfo file
class RebuildExportStrategy(ExportStrategy):
    JSONRPC_PROPS = [ 'file', 'title', 'genre', 'year', 'rating', 'director', 'trailer', 'tagline', 'plot', 'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer', 'studio', 'mpaa', 'cast', 'country', 'imdbnumber', 'runtime', 'set', 'showlink', 'streamdetails', 'top250', 'votes', 'fanart', 'thumbnail', 'sorttitle', 'resume', 'setid', 'dateadded', 'tag', 'art', 'userrating', 'ratings', 'premiered', 'uniqueid' ] # fields to be retrieved from library
    EXPORT_TAGS = [ 'title', 'originaltitle', 'sorttitle', 'ratings', 'top250', 'outline', 'plot', 'tagline', 'runtime', 'thumb', 'fanart', 'mpaa', 'playcount', 'lastplayed', 'id', 'uniqueid', 'genre', 'country', 'set', 'tag', 'credits', 'director', 'premiered', 'year', 'studio', 'trailer', 'fileinfo', 'actor', 'resume', 'dateadded' ] # tags to be inserted in nfo (see https://kodi.wiki/view/NFO_files/Movies); they will be processed sequentially in export()
    #EXCLUDED_TAGS = [ 'userrating', 'showlink' ] # userrating is added dynamically if settings is true (same as watched)

    # load the existing nfo, and modify exported tags only
    def make_xml(self):
        try:
            # build new XML content
            soup = BeautifulSoup('', 'html.parser')
            root = soup.new_tag(self.video_type)
            soup.append(root)

            # append child nodes
            for tag_name in self.export_tags:
                # filter specific processings
                if (tag_name == 'ratings'):
                    elt = soup.new_tag('ratings')
                    root.append(elt)
                    for src in self.video_details['ratings'].keys():
                        child = soup.new_tag('rating')
                        elt.append(child)
                        child['name'] = src
                        child['max'] = 10
                        if (self.video_details['ratings'][src]['default']):
                            child['default'] = 'true'
                        for val in ['rating', 'votes']:
                            gchild = soup.new_tag(val)
                            child.append(gchild)
                            gchild.string = str(self.video_details['ratings'][src][val])
                elif (tag_name == 'outline'):
                    elt = soup.new_tag('outline')
                    root.append(elt)
                    elt.string = str(self.video_details['plotoutline'])
                elif (tag_name == 'thumb'):
                    # multiple entries possibly, but not in Kodi library?
                    elt = soup.new_tag('thumb')
                    root.append(elt)
                    elt['aspect'] = 'poster'
                    elt['preview'] = ''
                    elt.string = str(self.video_details['art']['poster'])
                elif (tag_name == 'fanart'):
                    # multiple entries possibly, but not in Kodi library?
                    elt = soup.new_tag('fanart')
                    root.append(elt)
                    child = soup.new_tag('thumb')
                    elt.append(child)
                    child['preview'] = ''
                    child.string = str(self.video_details['art']['fanart'])
                elif (tag_name == 'id'):
                    elt = soup.new_tag('id')
                    root.append(elt)
                    elt.string = str(self.video_details['imdbnumber'])
                elif (tag_name == 'uniqueid'):
                    elt = soup.new_tag('uniqueid')
                    root.append(elt)
                    elt['type'] = 'unknown'
                    elt['default'] = 'true'
                    elt.string = str(self.video_details['imdbnumber'])
                elif (tag_name in [ 'genre', 'director', 'studio' ]):
                    # multiple entries, w/ same name in field and tag
                    for label in self.video_details[tag_name]:
                        elt = soup.new_tag(tag_name)
                        root.append(elt)
                        # TODO: set clear="true"?
                        elt['clear'] = 'true'
                        elt.string = label
                elif (tag_name == 'country'):
                    # multiple entries
                    for label in self.video_details['country']:
                        elt = soup.new_tag('country')
                        root.append(elt)
                        elt.string = label
                elif (tag_name == 'set'):
                    if (int(self.video_details['setid']) == 0):
                        continue
                    # here we need to grab some data
                    set_details = self.task.get_details(self.video_details['setid'], 'set', properties = ['title', 'plot']) # overload self.video_type to execute this specific query
                    elt = soup.new_tag('set')
                    root.append(elt)
                    # child: name
                    child = soup.new_tag('name')
                    elt.append(child)
                    child.string = set_details['title']
                    # child: overview
                    child = soup.new_tag('overview')
                    elt.append(child)
                    child.string = set_details['plot']
                elif (tag_name == 'tag'):
                    # multiple entries
                    for label in self.video_details['tag']:
                        elt = soup.new_tag('tag')
                        root.append(elt)
                        elt.string = label
                elif (tag_name == 'credits'):
                    # multiple entries
                    for label in self.video_details['writer']:
                        elt = soup.new_tag('credits')
                        root.append(elt)
                        # TODO: set clear="true"?
                        elt['clear'] = 'true'
                        elt.string = label
                elif (tag_name == 'fileinfo'):
                    elt1 = soup.new_tag('fileinfo')
                    root.append(elt1)
                    elt2 = soup.new_tag('streamdetails')
                    elt1.append(elt2)
                    # child: video (multiple)
                    for video_details in self.video_details['streamdetails']['video']:
                        child = soup.new_tag('video')
                        elt2.append(child)
                        for prop in [ 'codec', 'aspect', 'width', 'height', 'stereomode' ]:
                            gchild = soup.new_tag(prop)
                            child.append(gchild)
                            gchild.string = str(video_details[prop])
                        gchild = soup.new_tag('durationinseconds')
                        child.append(gchild)
                        gchild.string = str(video_details['duration'])
                    # child: audio (multiple)
                    for audio_details in self.video_details['streamdetails']['audio']:
                        child = soup.new_tag('audio')
                        elt2.append(child)
                        for prop in [ 'codec', 'language', 'channels' ]:
                            gchild = soup.new_tag(prop)
                            child.append(gchild)
                            gchild.string = str(audio_details[prop])
                    # child: subtitle (multiple)
                    for subtitle_details in self.video_details['streamdetails']['subtitle']:
                        child = soup.new_tag('subtitle')
                        elt2.append(child)
                        gchild = soup.new_tag('language')
                        child.append(gchild)
                        gchild.string = str(subtitle_details['language'])
                elif (tag_name == 'actor'):
                    # multiple entries
                    for actor_details in self.video_details['cast']:
                        elt = soup.new_tag('actor')
                        root.append(elt)
                        # TODO: set clear="true"?
                        elt['clear'] = 'true'
                        for prop in [ 'name', 'role', 'order' ]:
                            child = soup.new_tag(prop)
                            elt.append(child)
                            child.string = (u'%s' % actor_details[prop])
                        child = soup.new_tag('thumb')
                        elt.append(child)
                        child.string = actor_details.get('thumbnail') or ''
                elif (tag_name == 'resume'):
                    elt = soup.new_tag('resume')
                    root.append(elt)
                    for prop in [ 'position', 'total' ]:
                        child = soup.new_tag(prop)
                        elt.append(child)
                        child.string = (u'%s' % self.video_details['resume'][prop])
                else:
                    # default: add a simple element with value as text
                    elt = soup.new_tag(tag_name)
                    # copy value retrieved from library into the element
                    val = (u'%s' % self.video_details[tag_name])
                    elt.string = val
                    root.append(elt)
            self.soup = soup
            self.root = root
            # no old_raw, as we build from scratch
        except Exception as e:
            raise ExportStrategyError(self.nfo_path, 'error rebuilding nfo file', e)
