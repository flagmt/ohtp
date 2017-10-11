import requests
import json
import csv
from ratelimit import *


def check_city_state(query):
    new_q = query
    tokens = query.split()
    n = len(tokens)
    state_name = tokens[-1]
    if state_name in states.keys() and n == 2:
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
            c_s.append(city)
            c_s.append(coords)
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



#####################################################################################################################
# file paths
# path to directory of full corpus
full_path = 'corpus_complete'
# path to gazetteer
gaz_path = 'gazetteer_mod.txt'
#####################################################################################################################
"""
# load gazetteer into dictionary
with open(gaz_path, mode='r') as infile:
    reader = csv.reader(infile)
    # {name: [type, lat, lon]}
    gaz = {row[0].strip("'"): [row[1], row[2], row[3]] for row in reader}
"""
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
us_names = ['US', 'U.S.', 'USA', 'U.S.A.', 'United States of America', 'America']
############################################################
c_s = []
query = 'Tempe Arizona'
print(get_coords(query))
