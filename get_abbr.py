"""
Mike Taylor
Sep 2017
get state and other abbreviations from a file
"""
import csv


with open('states.txt', 'r', encoding='latin-1', newline='') as infile, open('abbr.txt', 'w', encoding='latin-1',
                                                                             newline='') as outfile:
    reader = csv.reader(infile, delimiter='\t')
    writer = csv.writer(outfile)
    for row in reader:
        abbr = row[0].split('.')[1]
        if len(row) == 6:
            state_name = row[1] + ' ' + row[2]
        else:
            state_name = row[1]
        abbr = abbr.strip()
        state_name = state_name.strip()
        line = state_name + ',' + abbr
        print(line)
        outfile.write(line + '\n')

