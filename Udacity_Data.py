#!/usr/bin/env python
# -*- coding: utf-8 -*-


import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint

osmfile = "C:/Users/Jason/map.osm"
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
            "Trail", "Parkway", "Commons"]

# UPDATE THIS VARIABLE
mapping = { "St":"Street",
            "St.":"Street",
            "Ave":"Avenue",
            "Ave.":"Avenue",
            "Rd.":"Road",
            "CT":"Court",
            "Pt":"Point",
            "Rd":"Road"
          }


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)


def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types



def update_name(name, mapping):
    data = street_type_re.search(name)
    if data:
        street_type = data.group()
        if street_type not in expected:
            name = re.sub(street_type_re, mapping[street_type], name)

    return name


import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "C:/Users/Jason/map.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # YOUR CODE HERE
    if element.tag == 'node':
        for a in node_attr_fields:
            node_attribs[a] = element.attrib[a]
        # print(node_attribs)

        for data in element.iter('tag'):
            hope = {}
            if PROBLEMCHARS.match(data.attrib['k']):
                break
            else:
                hope['id'] = element.attrib['id']
                hope['value'] = data.attrib['v']
                if ":" in data.attrib['k']:
                    val = data.attrib['k'].split(':', 1)
                    hope['type'] = val[0]
                    hope['key'] = val[1]
                else:
                    hope['type'] = 'regular'
                    hope['key'] = data.attrib['k']
                # print(hope)
            tags.append(hope)
        # print(tags)
        return {'node': node_attribs, 'node_tags': tags}


    elif element.tag == 'way':
        # print(maybe)
        for data, value in element.items():
            # print(data, value)
            if data in WAY_FIELDS:
                # print(data)
                way_attribs[data] = value

        for b in element.iter('tag'):
            maybe = {}
            # print(b)
            if PROBLEMCHARS.search(b.attrib['k']):
                pass
            else:
                maybe['id'] = element.attrib['id']
                # print(maybe['id'])
                maybe['value'] = b.attrib['v']
                # print(maybe['value'])
                #print(b.attrib['k'])
                if LOWER_COLON.search(b.attrib['k']):
                    maybe['key'] = ':'.join(b.attrib['k'].split(":")[1:])
                    maybe['type'] = str(b.attrib['k'].split(":")[0])
                else:
                    maybe['key'] = b.attrib['k']
                    maybe['type'] = 'regular'

            tags.append(maybe)
            # print({'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags})

        a = 0
        for c in element.iter('nd'):
            vader = {}
            vader['id'] = element.attrib['id']
            vader['node_id'] = c.attrib['ref']
            vader['position'] = a
            a += 1
            way_nodes.append(vader)
        # print({'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags})
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode() if isinstance(v, str) else v) for k, v in row.items()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
            codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
            codecs.open(WAYS_PATH, 'w') as ways_file, \
            codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
            codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()  #Code is erroring out here and I'm not sure why. 

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)
