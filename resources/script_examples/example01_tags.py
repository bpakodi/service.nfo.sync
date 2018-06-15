log.debug('hey, I can even log from here!')

# remove all existing <tag> nodes first
for elt in root.find_all('tag', recursive=False):
    elt.decompose()

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

# add all these new tags to root node
for tag_name in tags:
    elt = soup.new_tag('tag') # create a new node element
    elt.string = tag_name # set its string content
    root.append(elt) # add the node to root children
