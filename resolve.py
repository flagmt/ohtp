"""
Mike Taylor
Oct 2017
resolve toponyms in files
"""
import re
import os
import csv
import requests
import json
import queue
import simplekml
from math import log
import sys
from ratelimit import *
import itertools
# from requests.exceptions import ConnectionError
# import time


# check if topo is city-state combo, if yes, return new query as 'city, state'
def check_city_state(query):
    new_q = query
    tokens = query.split()
    n = len(tokens)
    state_name = tokens[-1]
    if state_name in states.keys():
        city_name = ' '.join(tokens[:n - 1])
        new_q = city_name + ', ' + state_name
        cs = True
        return new_q, cs
    else:
        state_name = ' '.join(tokens[-2:])
        if state_name in states.keys():
            city_name = ' '.join(tokens[:n - 2])
            new_q = city_name + ', ' + state_name
            cs = True
            return new_q, cs
    cs = False
    return new_q, cs


def wiki_data(query):
    tokens = query.split()
    candidate_title = tokens[0]
    # URL to wikipedia api
    base_url = 'https://en.wikipedia.org/w/api.php'
    # parameters for api, 'query' is passed into function
    payload = {'action': 'query', 'format': 'json', 'list': 'search', 'srsearch': query}
    # request data from api
    r = None
    while r is None:
        try:
            # create requests object, r, by sending request and payload
            r = requests.get(base_url, params=payload)
        except ConnectionError:
            print('ConnectionError:: pass')
            pass
    # load json data as a dict, 'j'
    j = json.loads(r.text)
    wordcounts = []
    try:
        for d in j['query']['search']:
            if candidate_title in d['title']:
                wordcounts.append(d['wordcount'])
    except KeyError:
        pass
    if wordcounts:
        max_count = max(wordcounts)
    else:
        max_count = 1
    return max_count


def get_weight(geo_type, query):
    num_words = wiki_data(query)
    num_words = num_words + 5
    if num_words > 500:
        w = 2.0
    if geo_type == 'Stream' or geo_type == 'Valley':
        w = 9.0
    elif geo_type == 'Post Office' or geo_type == 'Populated Place' or geo_type == 'Airport' or geo_type == 'Civil':
        w = 12.0
    elif geo_type == 'Rapids':
        w = 20.0
        num_words = num_words + 2500
    else:
        w = 0.25
    weight = log((w*num_words), 10)
    print('query: ', query, num_words, geo_type)
    return weight


def in_gaz(query):
    f_types = ['Populated Place', 'Post Office', 'Airport', 'Rapids', 'Valley', 'Stream', 'Locale']
    # if query in gaz.keys():
    for k in gaz.keys():
        if query in k:
            for item in gaz[k]:
                if item[0] in f_types:
                    return True


@rate_limited(3)
def check_geonames(payload, query):
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
    gaz_check = False
    geonames_result = json.loads(r.text)
    print(geonames_result)
    # check everything ok with result
    if geonames_result.get('status'):
        coords = None
        return coords
    gaz_check = in_gaz(query)
    # if desired results, return coords (lat, lon), else return None
    # cp_states = ['AZ', 'CO', 'UT', 'NM']
    if geonames_result.get('totalResultsCount') is not None and geonames_result.get('totalResultsCount'):
        lat = float(geonames_result.get('geonames')[0].get('lat'))
        lng = float(geonames_result.get('geonames')[0].get('lng'))
        # c_code = geonames_result.get('geonames')[0].get('countryCode')
        # admin_code = geonames_result.get('geonames')[0].get('adminCode1')
        population = geonames_result.get('geonames')[0].get('population')
        population = int(population)
        if population < 100000 and gaz_check:
            coords = None
            return coords
        coords = (round(lat, 4), round(lng, 4))
        # if admin_code not in cp_states:
        print(query, population)
        if ('EU' in payload or 'AS' in payload) and population < 100000:
            coords = None
            return coords
        else:
            return coords
    else:
        coords = None
        return coords


def get_coords(query):
    ########################################################################
    # http://api.geonames.org/search?name_equals=Snowflake&featureCode=PPL&username=flagmt
    # &cities5000&south=31&north=37&east=-109&west=-115&maxRows=1
    # Handle some toponyms using lists: us states, az counties, countries, continents
    ########################################################################
    query = query.strip()
    print('get_coords query is ' + query)
    coords = None
    if query in us_names:
        query = 'United States'
    # handle continents
    if query in continents.keys():
        coords = (continents[query][0], continents[query][1])
        return coords
    # handle US states + guam, puerto rico
    if query in states.keys():
        coords = (states[query][0], states[query][1])
        return coords
    # handle countries
    if query in countries.keys():
        coords = (countries[query][0], countries[query][1])
        return coords
    # handle arizona counties
    if query in counties.keys():
        coords = (counties[query][0], counties[query][1])
        return coords

    # convert query of form 'city state' to 'city, state'
    # if query is of this form change adminCode1 to state_abbr and search on city
    tokens = query.split()
    if len(tokens) > 1:
        query, cs = check_city_state(query)
        if cs:
            print('in cs: ', query)
            city_state = query.split(',')
            city = city_state[0].strip()
            state = city_state[1].strip()
            if len(state) > 2:
                state_abbr = abbr[state]
            else:
                state_abbr = state
            payload = {'username': 'flagmt', 'q': city, 'maxRows': 1, 'country': 'US', 'featureClass': 'P',
                       'orderby': 'population', 'adminCode1': state_abbr, 'isNameRequired': 'true'}
            coords = check_geonames(payload, query)
            return coords

    #
    # Handle European cities with population greater than 15000
    payload = {'username': 'flagmt', 'name_equals': query, 'maxRows': 1, 'orderby': 'population',
               'featureClass': 'P', 'cities': 'cities15000', 'continentCode': 'EU'}
    if check_geonames(payload, query):
        coords = check_geonames(payload, query)
        # print('other place: ' + query)
        return coords
    #
    #
    # Handle Asian cities with population greater than 15000
    payload = {'username': 'flagmt', 'name_equals': query, 'maxRows': 1, 'orderby': 'population',
               'featureClass': 'P', 'cities': 'cities15000', 'continentCode': 'AS'}
    if check_geonames(payload, query):
        coords = check_geonames(payload, query)
        # print('other place: ' + query)
        return coords
    #
    # Handle US cities with population greater than 15000
    payload = {'username': 'flagmt', 'q': query, 'maxRows': 1, 'orderby': 'population',
               'featureClass': 'P', 'cities': 'cities15000', 'country': 'US', 'isNameRequired': 'true'}
    if check_geonames(payload, query):
        coords = check_geonames(payload, query)
        # print('other place: ' + query)
        return coords

    # handle other cities
    payload = {'username': 'flagmt', 'q': query, 'maxRows': 1, 'orderby': 'population', 'isNameRequired': 'true',
               'featureClass': 'P'}  # , 'cities': 'cities1000'
    if check_geonames(payload, query):
        coords = check_geonames(payload, query)
        # print('other place: ' + query)
        return coords

    # else return None
    return coords


def get_candidates(name):
    # grab candidates from gazetteer whose name entry starts with toponym name. Example: 'Lava Falls' for 'Lava'
    # list will be of form: [[name, [type, lat, lon]], [name, [type, lat, lon]], ...]
    topo_tokens = name.split()
    print('get_candidates for ' + name)
    # get a list of candidates from the gazetteer
    candidates = []
    for k, v in gaz.items():
        if k.startswith(name):
            for item in v:
                candidates.append([k, item])

    if not candidates:
        name = name.split()[0]
        for k, v in gaz.items():
            if k.startswith(name):
                for item in v:
                    candidates.append([k, item])
    gaz_tokens = []
    for i, item in enumerate(candidates):
        gaz_tokens.append((i,item[0].split()))

    c_tmp = []
    for item in gaz_tokens:
        l = len(set(topo_tokens) & set(item[1]))
        if l > 1:
            c_tmp.append(candidates[item[0]])

    # print(c_tmp)
    if c_tmp:
        candidates = c_tmp
    if not candidates:
        candidates = None
        print('no candidates found for ' + name)
    # print(name, candidates)
    return candidates


def wiki(name):
    # add candidates to priority queue according to weight score
    p_queue = queue.PriorityQueue()
    candidates = get_candidates(name)
    if not candidates:
        p_queue.put((999, [name + ': not found in gazetteer', 0, 0]))
        return p_queue
    for candidate in candidates:
        p_candidate = [candidate[0], candidate[1][1], candidate[1][2]]
        weight = get_weight(candidate[1][0], candidate[0])
        # print('candidate: ' + candidate[0] + ', weight: ' + str(weight))
        p_queue.put(((1/weight), p_candidate))
    return p_queue

#####################################################################################################################
# file paths
# path to directory of full corpus
full_path = 'corpus_complete'
# path to gazetteer
gaz_path = 'gazetteer_mod.txt'
#####################################################################################################################
# load gazetteer into dictionary
gaz = {}
with open(gaz_path, mode='r') as infile:
    reader = csv.reader(infile)
    for row in reader:
        candidate = row[0].strip("'")
        feature_type = row[1]
        lat = row[2]
        lon = row[3]
        if candidate not in gaz:
            gaz[candidate] = [[feature_type, lat, lon]]
        else:
            gaz[candidate].append([feature_type, lat, lon])
##########################################################
# load states and their coordinates into a dictionary
# state coords from https://inkplant.com/code/state-latitudes-longitudes
# guam, puerto rico added by Mike Taylor
with open('state_coords.txt', mode='r') as infile:
    reader = csv.reader(infile)
    # {state: [lat, lon]}
    states = {row[0]: [row[1], row[2]] for row in reader}
#########################################################
# load state abbreviations into a dictionary
with open('state_abbr.txt', mode='r') as infile:
    reader = csv.reader(infile)
    # {state: abbr}
    abbr = {row[1]: row[0] for row in reader}
##########################################################
# load countries and their coordinates into a dictionary
# country coords from https://developers.google.com/public-data/docs/canonical/countries_csv
# england added by Mike Taylor
with open('countries.txt', mode='r') as infile:
    reader = csv.reader(infile)
    # {country: [lat, lon]}
    countries = {row[3]: [row[1], row[2]] for row in reader}
############################################################
# load counties and their coordinates into a dictionary
# county coords from https://www2.census.gov/geo/docs/maps-data/data/gazetteer/counties_list_04.txt
with open('counties.txt', mode='r') as infile:
    reader = csv.reader(infile)
    # {county: [lat, lon]}
    counties = {row[2]: [row[9], row[10]] for row in reader}
############################################################
# load continents and their coordinates into a dictionary
# coords from geonames.org
with open('continents.txt', mode='r') as infile:
    reader = csv.reader(infile)
    # {continent: [lat, lon]}
    continents = {row[0]: [row[1], row[2]] for row in reader}
############################################################
us_names = ['US', 'U.S.', 'USA', 'U.S.A.', 'United States of America', 'America', 'United States']
############################################################
resolved = {}
for filename in os.listdir(full_path):
    print(filename)
    base_name, ext = os.path.splitext(filename)
    # topo_list will initially hold all toponyms in one transcript
    # open a transcript and begin processing
    with open(full_path + '\\' + filename, 'r', encoding='latin-1') as full:
        # read in entire file contents as a string
        s = full.read()
        # locate each tagged toponym (tag = <toponym>) in s and place in list
        topo_list = re.findall(r'<(.*?)>', s)
        # remove apostrophes, replace St. with Saint (as it appears in gazetteer and geonames)
        for i, topo in enumerate(topo_list):
            topo_list[i] = topo.replace("'", "")
        for i, topo in enumerate(topo_list):
            topo_list[i] = topo.replace("St.", "Saint")
        for i, topo in enumerate(topo_list):
            topo_list[i] = topo.replace("Ft.", "Fort")

        # create a dictionary keyed on the toponyms from a transcript
        # this also has the effect of implementing the 'one sense per document' heuristic
        # since dictionary keys are unique

        doc_topos = {key: None for key in topo_list}
        for topo in doc_topos.keys():
            if doc_topos[topo]:
                continue
            # check if toponym already resolved
            elif topo in resolved.keys():
                doc_topos[topo] = resolved[topo]
                continue
            else:
                # use population heuristic to catch well-known toponyms
                doc_topos[topo] = get_coords(topo)
            # if not previously resolved and not resolved with population heuristic,
            # get candidates from gazetteer and calculate weights to select best candidate
            if not doc_topos[topo]:
                selected = wiki(topo)
                location = selected.get()
                doc_topos[topo] = (location[1][1], location[1][2])
            resolved[topo] = doc_topos[topo]
    # create a kml file for each transcript
    kml = simplekml.Kml()
    for key, val in doc_topos.items():
        kml.newpoint(name=key, coords=[(val[1], val[0])])
    kml.save('kml\\' + base_name + '.kml')
print('writing topos.txt...')
with open('topos__oct_7.txt', 'w', encoding='latin-1') as outfile:
    for k, v in resolved.items():
        outfile.write(k + ',' + str(v[0]) + ',' + str(v[1]) + '\n')
#######################################################################################################################
