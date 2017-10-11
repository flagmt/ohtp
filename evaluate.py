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

topos = {}
for filename in os.listdir('kml'):
    tree = ElementTree.parse(r'kml/' + filename)
    root = tree.getroot()
    for topo in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
        coords = topo[1][0].text.split(',')
        name = topo[0].text
        lat = coords[1]
        lon = coords[0]
        if name not in topos:
            if name in r_topos:
                topos[name] = (lat, lon)

error_dists = []
for k in topos.keys():
    lat1 = float(topos[k][0])
    lon1 = float(topos[k][1])
    lat2 = float(r_topos[k][0])
    lon2 = float(r_topos[k][1])
    d = haversine(lon1, lat1, lon2, lat2)
    # add error distances to a list
    error_dists.append(d)
    # calculate mean and median error distances

    if d > 161:
        print('error: ' + k + ', coords: ' + str(topos[k]))
    else:
        print(k)
med_err_dist = median(error_dists)
mean_err_dist = mean(error_dists)
print('mean error distance: ', mean_err_dist)
print('median error distance: ', med_err_dist)

