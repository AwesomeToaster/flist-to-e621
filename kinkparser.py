#! /usr/bin/python3

import json
import distance
import urllib.request, urllib.parse
import time
import re
import html
#from pprint import pprint

flist_kink_file = '/home/jimj316/Downloads/kink-list.json'
e621_tags_file = '/home/jimj316/Downloads/tags.json'

e621_tags = []

flist_replacements = {
    r'characters?'  : "", # strip "character" or "characters"
    r'giving'       : "", # giving and receiving are the same for images
    r'receiving'    : "", 
    r'play'         : "", # foot play, mouth play, etc.
    r' sex'         : "", # anal sex, oral sex, etc.
    r'e?s$'         : "", # remove plurals (probably pointless)
    r'(light|medium|heav(il)?y|extreme)':"",
    r'(very)'       : "", # e6 doesn't use very
    r'scenes( - )?'    : "", # fix "Scene - " kinks
    r'macro'        : "hyper", # e6 hyper tags are the highest they go
    r'ness'         : "",
    r'setting'      : "",
    r'semen'        : "cum",
    r'nonsexual'    : "",
    r'tiny'         : "small",
}

flist_syns = [
    ['dick','cock','penis'],
    ['vagina','pussy'],
    #['cum','semen'],
    ['large','big','huge'],
    ['swallow','drink','eat']
]

# read e621 tags

#with open(e621_tags_file) as json_data:
#     e621_data = json.load(json_data)

out = open("mapping.csv","w")

class Kink:
    flist_id = 0
    flist_name = ''
    flist_desc = ''
    search_strings = set()
    e621_id = ''
    e621_name = ''
    
    def __str__(self):
        return '{},{},{},{},"{}"'.format(self.flist_id,self.flist_name,self.e621_id,self.e621_name,self.flist_desc)
    
kinks = []

for i in range(1,30):
    #limit=1000&search[hide_empty]=yes&search[order]=count&page=2
    print("Reading e621 tags, page {}".format(i));
    params = {"limit": 1000, "search[hide_empty]": "yes", "search[order]": "count", "page": i}
    encoded_params = urllib.parse.urlencode(params)
    url = "https://e621.net/tags.json?" + encoded_params
    req = urllib.request.Request(
        url, 
        data=None, 
        headers={
            'User-Agent': 'KinkList/1.0 (by AwesomeToaster)'
        }
    )
    e621_data = json.load(urllib.request.urlopen(req))
    e621_tags.extend(e621_data)
    print("Got {} e621 tags.".format(len(e621_tags)));
    time.sleep(1)


# read f-list kinks

with open(flist_kink_file) as json_data:
    flist_data = json.load(json_data)
    
flist_kinks = flist_data['kinks'] # dictionary

for group_id in flist_kinks:
    group = flist_kinks[group_id] # dictionary
    items = group['items'] # array
    for flist_kink in items:
        kink = Kink()
        kink.flist_id = flist_kink['kink_id']
        kink.flist_name = html.unescape(flist_kink['name'])
        kink.flist_desc = flist_kink['description']
        
        # generate e621 search strings
        search_name = kink.flist_name.lower() # make the name lowercase
        
        kink.search_strings = {search_name}
        new_strings = set()
        
        for regex in flist_replacements: # eliminate common rubbish
            if re.search(regex, search_name):
                new_strings.add(re.sub(regex,flist_replacements[regex],search_name))
                
        kink.search_strings |= new_strings
        new_strings = set()
                
        for search in kink.search_strings:
            for syn_group in flist_syns:
                add_group = False
                for word in syn_group:
                    if word in search:
                        for word2 in syn_group:
                            if word2 != word:
                                new_strings.add(search.replace(word,word2))
                                
        kink.search_strings |= new_strings
        new_strings = set()
                
        for search in kink.search_strings:
            z = re.match(r'([\w/]+) ?[&/] ?([\w/]+)',search) # if there's a & or /
            if z:
                for word in z.groups():
                    new_strings.add(search.replace(z.group(),word))
                    
        kink.search_strings |= new_strings
        new_strings = set()
                    
        for search in kink.search_strings:
            z = re.match(r'^([^\(]+)\(([\w ]+)\)$',search)
            if z and len(z.groups()) >= 2:
                new_strings.add("{} {}".format(z.group(2),z.group(1)))
                new_strings.add(z.group(1))
                
        kink.search_strings |= new_strings
        new_strings = set()
                                
        kink.search_strings = [ # filter grammar
            search
            .replace('()','')
            .replace('(/)','')
            .strip()
            .replace(' / ','/')
            .replace(' & ','_and_')
            .replace(' ','_')
            for search in kink.search_strings
            ]
            
        kinks.append(kink)
            

def kink_key(kink):
    return kink.flist_id;

kinks.sort(key=kink_key)

kinks_out = []

# match kinks
for kink in kinks:
    matched = set();
    for search in kink.search_strings:
        print("Searching for match for {} ({})".format(kink.flist_name,search))
        max_ratio = 0.75
        best_tag = None
        
        for tag in e621_tags:
            tag_name = tag['name']
            dist = distance.levenshtein(search,tag_name)
            lensum = len(kink.flist_name)+len(tag_name)
            ratio = (lensum-dist)/lensum
            if ratio > max_ratio:
                max_ratio = ratio
                best_tag = tag
            if ratio == 1.0:
                break
                
        if best_tag is not None and not best_tag['id'] in matched:
            kink.e621_id = best_tag['id']
            kink.e621_name = best_tag['name']
    
            print(kink,file=out)
            matched.add(best_tag['id'])
    if len(matched) == 0:
        print(kink,file=out)
        
    
        
