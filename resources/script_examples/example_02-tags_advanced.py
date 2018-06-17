# The following variables are available:
#   soup:        BeautifulSoup object, basically the XML document. Useful for calling soup.new_tag(<tag_name>, <_tag_contents>)
#   root:        BeautifulSoup.Tag object, the root element of the document. Probably the (only) variable you should modify
#   log:         use this to add some text to log. Methods: debug(), info(), notice(), warning(), error(), fatal()
#   nfo_path:    path of the nfo file
#   video_path:  path of the video file
#   video_type:  movie / tvshow, ...
#   video_title: title of the movie / tvshow / ...

# import some standard modules
import os.path
import re

# build a new list of tags
tag_labels = set()

# check for tags based on file location
nfo_dir, nfo_file = os.path.split(nfo_path)
folder_filters = {
    'My cartoons':      'cartoons',
    'My comics movies': 'comics',
    'Favorites':        'favorites',
}
file_filters = {
    '.FRENCH.':         'audio: fr' # this may be a good improvement on just checking the audio stream language
}
for filter, tag_label in folder_filters.iteritems():
    if (re.search(r'\/%s\/?' % filter, nfo_dir)):
        tag_labels.add(tag_label)
for filter, tag_label in file_filters.iteritems():
    if (re.search(filter, nfo_file)):
        tag_labels.add(tag_label)

# remove all existing <tag> nodes from root
for elt in root.find_all('tag', recursive=False):
    elt.decompose()

# add all these new tags to root node
for tag_label in tag_labels:
    elt = soup.new_tag('tag') # create a new node element
    elt.string = tag_label # set its string content
    root.append(elt) # add the node to root children
log.debug('added tags to nfo: %s' % str(list(tag_labels)))
