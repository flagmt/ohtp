"""
Mike Taylor
Sept 2017
create a unique list of toponyms from the kml files with coords
"""
import os
from xml.etree import ElementTree
from math import sin, cos, sqrt, atan2, radians, asin
from statistics import median, mean


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

r_topos = {}
tree = ElementTree.parse('reference_topos.kml')
r_root = tree.getroot()
for topo in r_root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
    checked = True
    coords = topo[2][0].text.split(',')
    name = topo[0].text
    lat = coords[1]
    lon = coords[0]
    if name not in r_topos:
        r_topos[name] = (lat, lon)
        # print(name, r_topos[name])

file_errors = []
sum_scores = 0
sum_errors = 0
num_above_ninety = 0
for filename in os.listdir('kml'):
    tree = ElementTree.parse(r'kml/' + filename)
    root = tree.getroot()
    num_correct = 0
    num_errors = 0
    for topo in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
        coords = topo[1][0].text.split(',')
        name = topo[0].text
        lat1 = float(coords[1])
        lon1 = float(coords[0])
        lat2 = float(r_topos[name][0])
        lon2 = float(r_topos[name][1])
        d = haversine(lon1, lat1, lon2, lat2)
        if d > 161:
            num_errors = num_errors + 1
        else:
            num_correct = num_correct + 1
    print(filename, num_correct, num_errors, 100*(num_correct/(num_errors + num_correct)))
    if 100*(num_correct/(num_errors + num_correct)) == 100:
        num_above_ninety = num_above_ninety + 1
    sum_errors = sum_errors + num_errors
    sum_scores = sum_scores + 100*(num_correct/(num_errors + num_correct))
mean_scores = sum_scores/214
mean_errors = sum_errors/214
print(mean_scores, mean_errors, num_above_ninety)



