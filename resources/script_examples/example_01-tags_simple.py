# The following variables are available:
#   soup:        BeautifulSoup object, basically the XML document. Useful for calling soup.new_tag(<tag_name>, <_tag_contents>)
#   root:        BeautifulSoup.Tag object, the root element of the document. Probably the (only) variable you should modify
#   log:         use this to add some text to log. Methods: debug(), info(), notice(), warning(), error(), fatal()
#   nfo_path:    path of the nfo file
#   video_path:  path of the video file
#   video_type:  movie / tvshow, ...
#   video_title: title of the movie / tvshow / ...
#   task_family: 'import' or 'export'

log.debug('hey, I can even log from here!')

# build a new list of tags
tags = set()

# check for tag 'audio'
for elt in root.find_all('audio'):
    if (elt.language and elt.language.string == 'fre'):
        tags.add('audio: fr')

# check for tag 'subs'
for elt in root.find_all('subtitle'):
    if (elt.language and elt.language.string == 'fre'):
        tags.add('subs: fr')

# check for tag 'favorite actors'
for elt in root.find_all('actor'):
    if (elt.find('name') and elt.find('name').string == 'Jean-Claude Van Damme'): # 'name' is a reserved member in BeautifulSoup, so we must use elt.find('name') instead of elt.name
        tags.add('favorite actors: Jean-Claude Van Damme')

# check for tag 'video: 4k'
for elt in root.find_all('video'): # we probably have only one 'video' node, but just in case we loop through all of them
    try:
        if (elt.height and int(elt.height.string) == 2160):
            tag_labels.add('video: 4k')
    except ValueError: # conversion to int failed
        continue

# check for tag 'top 250' (IMDB top 250: https://www.imdb.com/chart/top)
for elt in root.find_all('top250'): # we probably have only one 'top250' node, but just in case we loop through all of them
    try:
        if (int(elt.string) > 0):
            tag_labels.add('top 250')
    except ValueError: # conversion to int failed
        continue

# remove all existing <tag> nodes from root
for elt in root.find_all('tag', recursive=False):
    elt.decompose()

# add all these new tags to root node
for tag_name in tags:
    elt = soup.new_tag('tag') # create a new node element
    elt.string = tag_name # set its string content
    root.append(elt) # add the node to root children
log.debug('added tags to nfo: %s' % str(list(tag_labels)))
