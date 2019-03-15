#!/usr/bin/env python3

from xml.dom.minidom import parseString
import requests
import re
import json
import os
import sys

exclude = [
    'Audiodeskription',
    'AD',
    'Hörfassung',
    'Vorschau',
    'Extra',
    'Trailer',
    'Making-of',
    'Tatort-Schnack',
    'Song zum Tatort'
]

download_dir = '/home/malte/Downloads/Tatort'
already_downloaded_file = './already_downloaded'

def should_exclude(title):
    for ex in exclude:
        if re.search(ex, title):
            return True
    return False

def add_to_downloaded_items(item):
    if not os.path.exists(already_downloaded_file):
        with open(already_downloaded_file, 'w') as f:
            json.dump([], f)

    down = []
    with open(already_downloaded_file, 'r') as f:
        down = json.load(f)
        down.append(item['guid'])

    with open(already_downloaded_file, 'w') as f:
        json.dump(down, f)

def download_item(item):
    if not 'dryrun' in sys.argv:
        print('Downloading "', item['title'], '"', sep='')
        with requests.get(item['link'], stream=True) as r:
            file_name = download_dir + '/' + item['title'] + '.mp4'
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
        add_to_downloaded_items(item)
    else:
        print('Downloading', item['title'])
        print('Adding', item['title'], 'to downloaded list')

def parse_rss(xml):
    dom = parseString(xml)
    collection = dom.documentElement
    channel = collection.getElementsByTagName('channel')

    ret = []
    titles = []
    items = channel[0].getElementsByTagName('item')
    for item in items:
        title = item.getElementsByTagName('title')[0].firstChild.wholeText
        link = item.getElementsByTagName('link')[0].firstChild.wholeText
        category = item.getElementsByTagName('category')[0].firstChild.wholeText
        guid = item.getElementsByTagName('guid')[0].firstChild.wholeText

        if category != 'Tatort':
            continue

        if should_exclude(title):
            continue

        if title in titles:
            continue

        ret.append({
            'title': title,
            'link': link,
            'category': category,
            'guid': guid
        })
    return ret

def filter_downloaded(items):
    if not os.path.exists(already_downloaded_file):
        with open(already_downloaded_file, 'w') as f:
            json.dump([], f)

    down = []
    with open(already_downloaded_file, 'r') as f:
        down = json.load(f)
    ret = []
    for item in items:
        if not item['guid'] in down:
            ret.append(item)
    return ret


if __name__ == '__main__':
    rss = requests.get('https://mediathekviewweb.de/feed?query=%23%22Tatort%22')

    if rss.status_code == 200:
        items = parse_rss(rss.text)
        items = filter_downloaded(items)

        for item in items:
            download_item(item)

    else:
        print('ERROR', rss)

