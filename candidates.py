"""
Mike Taylor
oct 2017
test get_candidates
"""
import csv
import requests
import json
import queue
from math import log
from math import sin, cos, sqrt, radians, asin


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
        print('candidate: ' + candidate[0] + ', weight: ' + str(weight))
        p_queue.put(((1/weight), p_candidate))
    return p_queue


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    from https://stackoverflow.com/questions/29545704/fast-haversine-approximation-python-pandas
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km

# load gazetteer into dictionary
gaz = {}
with open('gazetteer_mod.txt', mode='r') as infile:
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

topo = 'Vulcans Anvil'
selected = wiki(topo)
location = selected.get()
print(topo, location)
# print(haversine(-107.8683993, 37.2030582, -107.5695, 37.9314))
