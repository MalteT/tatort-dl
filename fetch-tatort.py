#!/usr/bin/env python3

from xml.dom.minidom import parseString
import requests
import re
import json
import os
from os.path import isfile
import sys


tatort_tvdb_id = '83214'

exclude = [
    'Audiodeskription',
    'AD',
    'Hörfassung',
    'Vorschau',
    'Extra',
    'Trailer',
    'Making-of',
    'Making of',
    'Tatort-Schnack',
    'Song zum Tatort'
]

download_dir = '/home/malte/Downloads/Tatort'
already_downloaded_file = './already_downloaded'

def get_tvdb_data():
    # Login
    r = requests.post('https://api.thetvdb.com/login', json={
        'apikey': apikey,
        'username': username,
        'userkey': userkey
    })
    if r.status_code == 200:
        token = json.loads(r.text)['token']
    else:
        print('Request to tvdb failed: {}'.format(r.text))
        sys.exit(1)
    # Get data
    data = []
    next_page = 1
    while next_page:
        print('Getting page: {}..'.format(next_page), end='', flush=True)
        r = requests.get('https://api.thetvdb.com/series/{}/episodes'
                .format(tatort_tvdb_id),
                headers={
                    'Authorization': 'Bearer {}'.format(token),
                    'Accept-Language': 'de',
                },
                params={
                    'page': next_page,
                })
        if r.status_code == 200:
            print('done')
            js = json.loads(r.text)
            next_page = js['links']['next']
            data += js['data']
        else:
            print('Request to tvdb failed: {}'.format(r.text))
            sys.exit(1)
    return data

def get_episode_infos():
    data = get_tvdb_data()
    info = []
    for el in data:
        if el['airedSeason'] == 0:
            continue
        if 'episodeName' in el and el['episodeName']:
            name = el['episodeName']
            parts = name.split(' - ', maxsplit=2)
            info.append({
                'name': parts[-1],
                'season': el['airedSeason'],
                'episode': el['airedEpisodeNumber'],
            })
    return info

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

def format_title(title):
    strip_from_front = [
        'Tatort: ',
        'Tatort - ',
        'Tatort – '
    ]
    strip_from_back = [
        ' (FSK 12)',
        ' (ab 12 Jahre)'
    ]
    title = title.strip()
    for front in strip_from_front:
        if title.startswith(front):
            title = title[len(front):]
    for back in strip_from_back:
        if title.endswith(back):
            title = title[:-len(back)]
    title = title.strip()
    for t in official_info:
        if t['name'] == title:
            return "S{:0>4}E{:0>2}".format(t['season'], t['episode'])
    return title

def download_item(item):
    path = download_dir + '/' + format_title(item['title']) + '.mp4'
    path_exists = isfile(path)
    while path_exists:
        path += '_'
    print("Downloading: {} -> {}".format(item['title'], path))
    if not 'dryrun' in sys.argv:
        with requests.get(item['link'], stream=True) as r:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
        add_to_downloaded_items(item)

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


official_info = get_episode_infos()

if __name__ == '__main__':
    rss = requests.get('https://mediathekviewweb.de/feed?query=%23%22Tatort%22')

    if rss.status_code == 200:
        items = parse_rss(rss.text)
        items = filter_downloaded(items)

        for item in items:
            download_item(item)

    else:
        print('ERROR', rss)

