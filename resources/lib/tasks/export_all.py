from __future__ import unicode_literals
import xbmcvfs
from bs4 import BeautifulSoup
from resources.lib.helpers import addon
from resources.lib.tasks import TaskFileError
from resources.lib.tasks.export_base import ExportTask, ExportTaskError

class ExportAllTaskError(ExportTaskError):
    pass

class ExportAllTask(ExportTask):
    JSONRPC_PROPS = [ 'file', 'title', 'genre', 'year', 'rating', 'director', 'trailer', 'tagline', 'plot', 'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer', 'studio', 'mpaa', 'cast', 'country', 'imdbnumber', 'runtime', 'set', 'showlink', 'streamdetails', 'top250', 'votes', 'fanart', 'thumbnail', 'sorttitle', 'resume', 'setid', 'dateadded', 'tag', 'art', 'userrating', 'ratings', 'premiered', 'uniqueid' ] # fields to be retrieved from library
    TAGS = [ 'title', 'originaltitle', 'sorttitle', 'ratings', 'top250', 'outline', 'plot', 'tagline', 'runtime', 'thumb', 'fanart', 'mpaa', 'playcount', 'lastplayed', 'id', 'uniqueid', 'genre', 'country', 'set', 'tag', 'credits', 'director', 'premiered', 'year', 'studio', 'trailer', 'fileinfo', 'actor', 'resume', 'dateadded' ] # tags to be inserted in nfo (see https://kodi.wiki/view/NFO_files/Movies); they will be processed sequentially in export()
    EXCLUDED_TAGS = [ 'userrating', 'showlink' ] # userrating is added dynamically if settings is true (same as watched)

    def __init__(self, monitor, video_type, video_id):
        super(ExportAllTask, self).__init__(monitor, video_type, video_id)

    # build a brand new nfo file
    def export(self):
        # TODO: manage access right issues
        try:
            # build new XML content
            soup = BeautifulSoup('', 'html.parser')
            root = soup.new_tag(self.video_type)
            soup.append(root)

            # append child nodes
            for tag_name in self.tags:
                # filter specific processings
                if (tag_name == 'ratings'):
                    elt = soup.new_tag('ratings')
                    root.append(elt)
                    for src in self.details['ratings'].keys():
                        child = soup.new_tag('rating')
                        elt.append(child)
                        child['name'] = src
                        child['max'] = 10
                        if (self.details['ratings'][src]['default']):
                            child['default'] = 'true'
                        for val in ['rating', 'votes']:
                            gchild = soup.new_tag(val)
                            child.append(gchild)
                            gchild.string = str(self.details['ratings'][src][val])
                elif (tag_name == 'outline'):
                    elt = soup.new_tag('outline')
                    root.append(elt)
                    elt.string = str(self.details['plotoutline'])
                elif (tag_name == 'thumb'):
                    # multiple entries possibly, but not in Kodi library?
                    elt = soup.new_tag('thumb')
                    root.append(elt)
                    elt['aspect'] = 'poster'
                    elt['preview'] = ''
                    elt.string = str(self.details['art']['poster'])
                elif (tag_name == 'fanart'):
                    # multiple entries possibly, but not in Kodi library?
                    elt = soup.new_tag('fanart')
                    root.append(elt)
                    child = soup.new_tag('thumb')
                    elt.append(child)
                    child['preview'] = ''
                    child.string = str(self.details['art']['fanart'])
                elif (tag_name == 'id'):
                    elt = soup.new_tag('id')
                    root.append(elt)
                    elt.string = str(self.details['imdbnumber'])
                elif (tag_name == 'uniqueid'):
                    elt = soup.new_tag('uniqueid')
                    root.append(elt)
                    elt['type'] = 'unknown'
                    elt['default'] = 'true'
                    elt.string = str(self.details['imdbnumber'])
                elif (tag_name in [ 'genre', 'director', 'studio' ]):
                    # multiple entries, w/ same name in field and tag
                    for label in self.details[tag_name]:
                        elt = soup.new_tag(tag_name)
                        root.append(elt)
                        # TODO: set clear="true"?
                        elt['clear'] = 'true'
                        elt.string = label
                elif (tag_name == 'country'):
                    # multiple entries
                    for label in self.details['country']:
                        elt = soup.new_tag('country')
                        root.append(elt)
                        elt.string = label
                elif (tag_name == 'set'):
                    if (int(self.details['setid']) == 0):
                        continue
                    # here we need to grab some data
                    set_details = self.get_details(self.details['setid'], 'set', properties = ['title', 'plot']) # overload self.video_type to execute this specific query
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
                    for label in self.details['tag']:
                        elt = soup.new_tag('tag')
                        root.append(elt)
                        elt.string = label
                elif (tag_name == 'credits'):
                    # multiple entries
                    for label in self.details['writer']:
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
                    for video_details in self.details['streamdetails']['video']:
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
                    for audio_details in self.details['streamdetails']['audio']:
                        child = soup.new_tag('audio')
                        elt2.append(child)
                        for prop in [ 'codec', 'language', 'channels' ]:
                            gchild = soup.new_tag(prop)
                            child.append(gchild)
                            gchild.string = str(audio_details[prop])
                    # child: subtitle (multiple)
                    for subtitle_details in self.details['streamdetails']['subtitle']:
                        child = soup.new_tag('subtitle')
                        elt2.append(child)
                        gchild = soup.new_tag('language')
                        child.append(gchild)
                        gchild.string = str(subtitle_details['language'])
                elif (tag_name == 'actor'):
                    # multiple entries
                    for actor_details in self.details['cast']:
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
                        child.string = (u'%s' % self.details['resume'][prop])
                else:
                    # default: add a simple element with value as text
                    elt = soup.new_tag(tag_name)
                    # copy value retrieved from library into the element
                    val = (u'%s' % self.details[tag_name])
                    elt.string = val
                    root.append(elt)

            # write content to NFO file
            self.save_nfo(self.nfo_path, root)
        except Exception as e:
            self.log.error('error caught while creating nfo file: %s: %s' % (e.__class__.__name__, e))
            # raise
            return False

        return True
