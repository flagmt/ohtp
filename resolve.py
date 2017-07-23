"""
Mike Taylor
April 2017
tag toponyms in files
"""
import re
import os
import csv
from ratelimit import *
import requests
import json
import pandas as pd
import wikipedia
import requests
import json
import queue


def gen_search(query):
    rapid = False
    # URL to wikipedia api
    base_url = 'https://en.wikipedia.org/w/api.php'
    # parameters fro api, 'query' is passed into function
    payload = {'action': 'query', 'format': 'json', 'list': 'search', 'srsearch': query}
    # request data from api
    r = requests.get(base_url, params=payload)
    # load json data as a dict, 'j'
    j = json.loads(r.text)
    # page id is unknown ahead of time, convert dict to list to access pageviews key
    h = j['query']['searchinfo']['totalhits']
    for d in j['query']['search']:
        if d['title'] == 'List of Colorado River rapids and features':
            rapid = True
    return h, rapid


def get_views(query):
    # URL to wikipedia api
    base_url = 'https://en.wikipedia.org/w/api.php'
    # parameters fro api, 'query' is passed into function
    payload = {'action': 'query', 'format': 'json', 'prop': 'pageviews', 'titles': query}  # prop=pageviews|coordinates
    # request data from api
    print(query)
    r = requests.get(base_url, params=payload)
    # load json data as a dict, 'j'
    j = json.loads(r.text)
    # page id is unknown ahead of time, convert dict to list to access pageviews key
    try:
        l = list(j["query"]["pages"].values())[0]["pageviews"]
    except (TypeError, KeyError):           # KeyError: 'query'
        avg_views = 1
        return avg_views
    # calculate average number of page views and return that value
    s = 0
    num_zeroes = 0
    for k, v in l.items():
        if l[k] is None:
            num_zeroes = num_zeroes + 1
            l[k] = 0
    # max page views, currently not used
    # m = max(l.values())
    for value in l.values():
        if not value:
            value = 0
        s = s + value
    avg_views = int(s/len(l.values()))
    return avg_views


def get_weight(lat, lon, query):
    p = 1
    result_list = wikipedia.geosearch(lat, lon, title=query)
    results, rapid = gen_search(query)
    num_hits = results + 1
    if query in result_list:
        w = 3.0
        p = get_views(query) + 1
    elif num_hits > 0:
        w = 1.25
    else:
        w = 0.25
    if rapid:
        w = 200.0
    weight = round(1/(w*(p + num_hits/100)), 5)
    # weight = (p + num_hits)/w
    return weight


@rate_limited(1, 2)
# if populated place with pop > 1000, returns coordinates of place, else returns None
def check_geonames(query, code='', country='', az=False, city=False, sw=False, fuzzy=1.0):
    ########################################################################
    # check geonames for well-known places (ie, Chicago)
    # if found, label in place. These would be ignored in further processing
    # use geonames 'fuzzy' feature ([0.0, 1.0], 1.0 only handles correctly spelled words)
    # to account for bad spelling like 'Albuquerk'
    # http://api.geonames.org/search?name_equals=Snowflake&featureCode=PPL&username=flagmt
    # &cities5000&south=31&north=37&east=-109&west=-115&maxRows=1
    ########################################################################
    # setup parameters to be passed to api, query variable is toponym passed into function
    if not az and not city:
        payload = {'username': 'flagmt', 'maxRows': 1, 'name_equals': query,
                   'featureCode': code, 'country': country, 'fuzzy': fuzzy}
    elif not az and city and sw:
        payload = {'username': 'flagmt', 'maxRows': 1, 'q': query,
                   'orderby': 'population', 'fuzzy': fuzzy, 'country': country,
                   'featureClass': 'P', 'cities': 'cities1000',
                   'north': '42', 'east': '-103', 'south': '31', 'west': '-125'}
                   ###  'featureClass': 'P', 'cities': 'cities1000', 'adminCode1': ['NM', 'CA', 'UT', 'CO']}
    elif not az and city and not sw:
        payload = {'username': 'flagmt', 'maxRows': 1, 'q': query,
                   'orderby': 'population', 'fuzzy': fuzzy, 'country': country,
                   'featureClass': 'P'}  # 'cities': 'cities15000'
    else:
        payload = {'username': 'flagmt', 'maxRows': 1, 'name_equals': query, 'fuzzy': fuzzy, 'code': code,
                   'adminCode1': 'az', 'country': country, 'featureClass': 'P'}
    # use req_results
    r = None
    while r is None:
        try:
            # create requests object, r, by sending request and payload
            r = requests.get('http://api.geonames.org/searchJSON', params=payload)
        except:
            pass
    if r.status_code != 200:
        print('Cannot call API: {}'.format(r.status_code))
        exit()
    # r.text is data returned from api request
    geonames_result = json.loads(r.text)
    # check everything ok with result
    if geonames_result.get('status'):
        print(geonames_result.get('status'))
    # if desired results, return coords (lat, lon), else return None
    if geonames_result.get('totalResultsCount') is not None and geonames_result.get('totalResultsCount') != 0:
        lat = float(geonames_result.get('geonames')[0].get('lat'))
        lng = float(geonames_result.get('geonames')[0].get('lng'))
        coords = (round(lat, 4), round(lng, 4))
        return coords
    else:
        coords = None
        return coords


def get_coords(topo):
    coords = None
    # handle continents
    if topo in {'Africa', 'Asia', 'Europe', 'North America', 'Oceania', 'South America', 'Antarctica'}:
        coords = check_geonames(topo)
        return coords
    # handle US states
    elif check_geonames(topo, code='ADM1', country='US'):
        coords = check_geonames(topo, code='ADM1', country='US')
        return coords
    # handle Arizona cities
    elif check_geonames(topo, country='US', az=True):
        coords = check_geonames(topo, country='US', az=True)
        return coords
    # handle other large cities outside Arizona, but still in southwest
    elif check_geonames(topo, city=True, sw=True, country='US'):
        coords = check_geonames(topo, city=True, sw=True, country='US')
        return coords
    # handle large cities outside the southwest
    elif check_geonames(topo, city=True):
        coords = check_geonames(topo, city=True)
        return coords


def replace_tag(topo, coords, s):
    # adding '?' to the regex pattern makes it less greedy, ie, it only matches the first set of parentheses
    pattern = '<' + topo + ', ' + r'\(.*?\)' + '>'
    # add coords to tag
    replace = '<' + topo + ', ' + coords + '>'
    r = re.sub(pattern, replace, s)
    # return the updated string
    return r


def get_candidates(topo, gaz_path):
    # read in gazetteer as a pandas dataframe
    gaz_df = pd.read_csv(gaz_path, header=0, encoding='utf-8')
    # create dataframe of entries from gazetteer that contain toponym
    df_candidates = gaz_df[gaz_df.name.str.startswith(topo)]
    if df_candidates.empty:
        df_candidates.name = 'none'
        df_candidates.lat = 0.0
        df_candidates.lon = 0.0
    df_candidates.round({'lat': 4, 'lon': 4})
    return df_candidates


def geo(full_path, list_path):
    for filename in os.listdir(full_path):
        with open(full_path + '\\' + filename, 'r', encoding='latin-1') as full:
            s = full.read()
            with open(list_path + '\\' + filename, 'r') as list:
                for topo in list:
                    topo = topo.rstrip('\n')
                    topo = topo.strip()
                    coords = get_coords(topo)
                    s = replace_tag(topo, str(coords), s)
        with open(full_path + '\\' + filename, 'w', encoding='utf8') as output:
            output.write(s)
    return


def wiki(topo, gaz_path):
    p_queue = queue.PriorityQueue()
    df = get_candidates(topo, gaz_path)
    if df.empty:
        p_queue.put((999, [topo + ': not found in gazetteer', 0, 0]))
        return p_queue
    for index, row in df.iterrows():
        # print(row['name'], round(row['lat'], 4), round(row['lon'], 4), get_weight(row['lat'], row['lon'], row['name']))
        candidate = [row['name'], round(row['lat'], 4), round(row['lon'], 4)]
        weight = get_weight(row['lat'], row['lon'], row['name'])
        p_queue.put((weight, candidate))
    return p_queue


#####################################################################################################################
#
# file paths
# path to directory of full text
# full_path = r'C:\Users\met28\OneDrive - Northern Arizona University\full'
# full_path = r'C:\corpus'
full_path = 'corpus'
# path to directory of toponym lists for each full text file - same names
# list_path = r'C:\Users\met28\OneDrive - Northern Arizona University\list'
# path to gazetteer
# gaz_path = r'C:\Users\met28\OneDrive - Northern Arizona University\Shared with Everyone\cp_place_names\gazetteer.txt'
gaz_path = 'gazetteer.txt'
#####################################################################################################################

resolved = {}
for filename in os.listdir(full_path):
    print(filename)
    topo_list = []
    with open(full_path + '\\' + filename, 'r', encoding='latin-1') as full:
        # read in entire file contents as a string
        s = full.read()
        # locate each tagged toponym (tag = <toponym, ()>) and place in list
        topo_list = re.findall(r'<(.*?),', s)
        for topo in topo_list:
            # one sense per document heuristic
            if topo in resolved.keys() and resolved[topo]:
                s = replace_tag(topo, str(resolved[topo]), s)
                continue
            # use population heuristic to catch well-known toponyms
            else:
                resolved[topo] = get_coords(topo)
            # calculate weights to select a candidate
            if not resolved[topo]:
                selected = wiki(topo, gaz_path)
                location = selected.get()
                resolved[topo] = (location[1][1], location[1][2])
            s = replace_tag(topo, str(resolved[topo]), s)
    with open(full_path + '\\' + filename, 'w', encoding='latin-1') as output:
        output.write(s)
# write each unique toponym and its 'found' coordinates to a file
w = csv.writer(open("C:\corpus_test\output.csv", "w", encoding='latin-1'))
for key, val in resolved.items():
    w.writerow([key, val])

#######################################################################################################################
