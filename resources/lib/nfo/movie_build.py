from __future__ import unicode_literals

import resources.lib.library as Library
LibraryError = Library.LibraryError # just as a convenience
from resources.lib.nfo import NFOBuildHandler, NFOHandlerError

# build the NFO from scratch
# only applicable to movies
class MovieNFOBuildHandler(NFOBuildHandler):
    JSONRPC_PROPS = [ 'file', 'title', 'genre', 'year', 'rating', 'director', 'trailer', 'tagline', 'plot', 'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer', 'studio', 'mpaa', 'cast', 'country', 'imdbnumber', 'runtime', 'set', 'showlink', 'streamdetails', 'top250', 'votes', 'fanart', 'thumbnail', 'sorttitle', 'resume', 'setid', 'dateadded', 'tag', 'art', 'userrating', 'ratings', 'premiered', 'uniqueid' ] # fields to get from library
    EXPORT_TAGS = [ 'title', 'originaltitle', 'sorttitle', 'ratings', 'top250', 'outline', 'plot', 'tagline', 'runtime', 'thumb', 'fanart', 'mpaa', 'playcount', 'lastplayed', 'id', 'uniqueid', 'genre', 'country', 'set', 'tag', 'credits', 'director', 'premiered', 'year', 'studio', 'trailer', 'fileinfo', 'actor', 'resume', 'dateadded' ] # tags to generate; they will be processed sequentially in make_xml()
    #EXCLUDED_TAGS = [ 'userrating', 'showlink' ] # userrating is added dynamically if settings is true (same as watched)

    # called from loop in make_xml()
    def build_tag(self, tag_name):
        # filter specific processings
        if (tag_name == 'ratings'):
            elt = self.soup.new_tag('ratings')
            self.root.append(elt)
            for src in self.entry['ratings'].keys():
                child = self.soup.new_tag('rating')
                elt.append(child)
                child['name'] = src
                child['max'] = 10
                if (self.entry['ratings'][src]['default']):
                    child['default'] = 'true'
                for val in ['rating', 'votes']:
                    gchild = self.soup.new_tag(val)
                    child.append(gchild)
                    gchild.string = str(self.entry['ratings'][src][val])
        elif (tag_name == 'outline'):
            self.add_tag('outline', str(self.entry['plotoutline']))
        elif (tag_name == 'thumb'):
            # multiple entries possibly, but not in Kodi library?
            elt = self.add_tag('thumb', str(self.entry['art']['poster']))
            elt['aspect'] = 'poster'
            elt['preview'] = ''
        elif (tag_name == 'fanart'):
            # multiple entries possibly, but not in Kodi library?
            child = self.soup.new_tag('thumb')
            child['preview'] = ''
            child.string = str(self.entry['art']['fanart'])
            self.add_tag('fanart', child)
        elif (tag_name == 'id'):
            self.add_tag('id', str(self.entry['imdbnumber']))
        elif (tag_name == 'uniqueid'):
            elt = self.add_tag('uniqueid', str(self.entry['imdbnumber']))
            elt['type'] = 'unknown'
            elt['default'] = 'true'
        elif (tag_name in [ 'genre', 'director', 'studio' ]):
            # multiple entries, w/ same name in field and tag
            for label in self.entry[tag_name]:
                elt = self.add_tag(tag_name, label)
                # TODO: set clear="true"?
                elt['clear'] = 'true'
        elif (tag_name in [ 'country', 'tag' ]):
            # multiple entries
            for label in self.entry[tag_name]:
                self.add_tag(tag_name, label)
        elif (tag_name == 'set'):
            if (int(self.entry['setid']) == 0):
                continue
            # here we need to grab some data
            set_details = Library.get_details(self.entry['setid'], 'set', properties = ['title', 'plot']) # overload self.video_type to execute this specific query
            elt = self.soup.new_tag('set')
            self.root.append(elt)
            # child: name
            child = self.soup.new_tag('name')
            elt.append(child)
            child.string = set_details['title']
            # child: overview
            child = self.soup.new_tag('overview')
            elt.append(child)
            child.string = set_details['plot']
        elif (tag_name == 'credits'):
            # multiple entries
            for label in self.entry['writer']:
                elt = self.add_tag('credits', label)
                # TODO: set clear="true"?
                elt['clear'] = 'true'
        elif (tag_name == 'fileinfo'):
            elt1 = self.soup.new_tag('fileinfo')
            self.root.append(elt1)
            elt2 = self.soup.new_tag('streamdetails')
            elt1.append(elt2)
            # child: video (multiple)
            for video_details in self.entry['streamdetails']['video']:
                child = self.soup.new_tag('video')
                elt2.append(child)
                for prop in [ 'codec', 'aspect', 'width', 'height', 'stereomode' ]:
                    gchild = self.soup.new_tag(prop)
                    child.append(gchild)
                    gchild.string = str(video_details[prop])
                gchild = self.soup.new_tag('durationinseconds')
                child.append(gchild)
                gchild.string = str(video_details['duration'])
            # child: audio (multiple)
            for audio_details in self.entry['streamdetails']['audio']:
                child = self.soup.new_tag('audio')
                elt2.append(child)
                for prop in [ 'codec', 'language', 'channels' ]:
                    gchild = self.soup.new_tag(prop)
                    child.append(gchild)
                    gchild.string = str(audio_details[prop])
            # child: subtitle (multiple)
            for subtitle_details in self.entry['streamdetails']['subtitle']:
                child = self.soup.new_tag('subtitle')
                elt2.append(child)
                gchild = self.soup.new_tag('language')
                child.append(gchild)
                gchild.string = str(subtitle_details['language'])
        elif (tag_name == 'actor'):
            # multiple entries
            for actor_details in self.entry['cast']:
                elt = self.soup.new_tag('actor')
                self.root.append(elt)
                # TODO: set clear="true"?
                elt['clear'] = 'true'
                for prop in [ 'name', 'role', 'order' ]:
                    child = self.soup.new_tag(prop)
                    elt.append(child)
                    child.string = (u'%s' % actor_details[prop])
                child = self.soup.new_tag('thumb')
                elt.append(child)
                child.string = actor_details.get('thumbnail') or ''
        elif (tag_name == 'resume'):
            elt = self.soup.new_tag('resume')
            self.root.append(elt)
            for prop in [ 'position', 'total' ]:
                child = self.soup.new_tag(prop)
                elt.append(child)
                child.string = (u'%s' % self.entry['resume'][prop])
        else:
            # get default value from library entry details
            self.add_tag(tag_name)
