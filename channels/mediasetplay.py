# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# Canale per Mediaset Play
# ------------------------------------------------------------

from platformcode import logger, config
import uuid, datetime, xbmc

import requests, sys
from core import support
if sys.version_info[0] >= 3:
    from urllib.parse import urlencode, quote
else:
    from urllib import urlencode, quote

host = 'https://www.mediasetplay.mediaset.it'
loginUrl = 'https://api-ott-prod-fe.mediaset.net/PROD/play/idm/anonymous/login/v2.0'

clientid = 'f66e2a01-c619-4e53-8e7c-4761449dd8ee'


loginData = {"client_id": clientid, "platform": "pc", "appName": "web//mediasetplay-web/5.1.493-plus-da8885b"}
sessionUrl = "https://api.one.accedo.tv/session?appKey=59ad346f1de1c4000dfd09c5&uuid={uuid}&gid=default"

session = requests.Session()
session.headers.update({'Content-Type': 'application/json', 'User-Agent': support.httptools.get_user_agent(), 'Referer': host})

entry = 'https://api.one.accedo.tv/content/entry/{id}?locale=it'
entries = 'https://api.one.accedo.tv/content/entries?id={id}&locale=it'

# login anonimo
res = session.post(loginUrl, json=loginData, verify=False)
Token = res.json()['response']['beToken']
sid = res.json()['response']['sid']
session.headers.update({'authorization': 'Bearer ' + Token})

# sessione
sessionKey = session.get(sessionUrl.format(uuid=str(uuid.uuid4())), verify=False).json()['sessionKey']
session.headers.update({'x-session': sessionKey})


@support.menu
def mainlist(item):
    top =  [('Dirette {bold}', ['', 'live'])]

    menu = [('Fiction / Serie TV {bullet bold}', ['/fiction', 'menu', '5acfcb3c23eec6000d64a6a4', 'tvshow']),
            ('Programmi TV{ bullet bold}', ['/programmitv', 'menu', '5acfc8011de1c4000b6ec953', 'tvshow']),
            ('Documentari {bullet bold}', ['/documentari', 'menu', '5bfd17c423eec6001aec49f9', 'undefined']),
            ('Kids {bullet bold}', ['/kids', 'menu', '5acfcb8323eec6000d64a6b3', 'undefined'])]

    search = ''
    return locals()

def menu(item):
    logger.debug()
    itemlist = []
    res = get_from_id(item)
    for it in res:
        if 'uxReference' in it:
            itemlist.append(item.clone(title=support.typo(it['title'], 'bullet bold'),
                            url= it['landingUrl'],
                            feed = it.get('feedurlV2',''),
                            ref=it.get('uxReferenceV2', ''),
                            params=it.get('uxReferenceV2Params', ''),
                            args='',
                            action='peliculas'))
    return itemlist


def live(item):
    itemlist = []

    res = session.get('https://static3.mediasetplay.mediaset.it/apigw/nownext/nownext.json').json()['response']
    allguide = res['listings']
    stations = res['stations']

    for it in stations.values():
        plot = ''
        title = it['title']
        url = 'https:' + it['mediasetstation$pageUrl']
        if 'plus' in title.lower() or 'premium' in title.lower(): continue
        if it['callSign'] in allguide:

            guide = allguide[it['callSign']]
            plot = '[B]{}[/B]\n{}\n\nA Seguire:\n[B]{}[/B]\n{}'.format(guide['currentListing']['mediasetlisting$epgTitle'],
                                                                        guide['currentListing']['description'],
                                                                        guide['nextListing']['mediasetlisting$epgTitle'],
                                                                        guide['nextListing']['description'],)

            itemlist.append(item.clone(title=support.typo(title, 'bold'), fulltitle=title, callSign=it['callSign'], urls=guide['tuningInstruction']['urn:theplatform:tv:location:any'], plot=plot, url=url, action='play', forcethumb=True))

    itemlist.sort(key=lambda it: support.channels_order.get(it.fulltitle, 999))
    support.thumb(itemlist, live=True)
    return itemlist


def search(item, text):
    item.ref = 'main'
    item.query = text
    item.params = 'channel≈'

    try:
        return peliculas(item)
    # Continua la ricerca in caso di errore
    except:
        import sys
        for line in sys.exc_info():
            support.logger.error("%s" % line)
        return []


def peliculas(item):
    itemlist = []
    res = get_programs(item)
    video_id= ''

    for it in res['items']:
        if not 'MediasetPlay_ANY' in it.get('mediasetprogram$channelsRights',['MediasetPlay_ANY']): continue
        thumb = ''
        fanart = ''
        contentSerieName = ''
        url = 'https:'+ it.get('mediasettvseason$pageUrl', it.get('mediasetprogram$videoPageUrl', it.get('mediasetprogram$pageUrl')))
        title = it.get('mediasetprogram$brandTitle', it.get('title'))
        title2 = it['title']
        if title != title2:
            title = '{} - {}'.format(title, title2)
        plot = it.get('longDescription', it.get('description', it.get('mediasettvseason$brandDescription', '')))

        if it.get('seriesTitle') or it.get('seriesTvSeasons'):
            contentSerieName = it.get('seriesTitle', it.get('title'))
            contentType = 'tvshow'
            action = 'epmenu'
        else:
            contentType = 'movie'
            video_id = it['guid']
            action = 'play'
        for k, v in it['thumbnails'].items():
            if 'image_vertical' in k and not thumb:
                thumb = v['url'].replace('.jpg', '@3.jpg')
            if 'image_header_poster' in k and not fanart:
                fanart = v['url'].replace('.jpg', '@3.jpg')
            if thumb and fanart:
                break

        itemlist.append(item.clone(title=support.typo(title, 'bold'),
                                   fulltitle=title,
                                   contentTitle=title,
                                   contentSerieName=contentSerieName,
                                   action=action,
                                   contentType=contentType,
                                   thumbnail=thumb,
                                   fanart=fanart,
                                   plot=plot,
                                   url=url,
                                   video_id=video_id,
                                   seriesid = it.get('seriesTvSeasons', it.get('id','')),
                                   forcethumb=True))
    if res['next']:
        item.page = res['next']
        support.nextPage(itemlist, item)

    return itemlist

def epmenu(item):
    logger.debug()
    itemlist = []

    epUrl = 'https://feed.entertainment.tv.theplatform.eu/f/PR1GhC/mediaset-prod-all-subbrands-v2?byTvSeasonId={}&sort=mediasetprogram$order'

    if item.seriesid:
        if type(item.seriesid) == list:
            res = []
            for s in item.seriesid:
                itemlist.append(
                    item.clone(seriesid = s['id'],
                               title=support.typo(s['title'], 'bold')))
            if len(itemlist) == 1: return epmenu(itemlist[0])
        else:
            res = requests.get(epUrl.format(item.seriesid)).json()['entries']
            for it in res:
                itemlist.append(
                    item.clone(seriesid = '',
                               title=support.typo(it['description'], 'bold'),
                               subbrand=it['mediasetprogram$subBrandId'],
                               action='episodios'))
            itemlist = sorted(itemlist, key=lambda it: it.title, reverse=True)
            if len(itemlist) == 1: return episodios(itemlist[0])

    return itemlist

def episodios(item):
    # create month list
    months = []
    try:
        for month in range(21, 33): months.append(xbmc.getLocalizedString(month))
    except:  # per i test, xbmc.getLocalizedString non è supportato
        for month in range(21, 33): months.append('dummy')

    itemlist = []
    res = requests.get('https://feed.entertainment.tv.theplatform.eu/f/PR1GhC/mediaset-prod-all-programs-v2?byCustomValue={subBrandId}{' + item.subbrand +'}&sort=:publishInfo_lastPublished|asc,tvSeasonEpisodeNumber').json()['entries']

    for it in res:
        thumb = ''
        titleDate = ''
        if 'mediasetprogram$publishInfo_lastPublished' in it:
            date = datetime.date.fromtimestamp(it['mediasetprogram$publishInfo_lastPublished'] / 1000)
            titleDate ='  [{} {}]'.format(date.day, months[date.month])
        title = '[B]{}[/B]{}'.format(it['title'], titleDate)
        for k, v in it['thumbnails'].items():
            if 'image_keyframe' in k and not thumb:
                thumb = v['url'].replace('.jpg', '@3.jpg')
                break
        if not thumb: thumb = item.thumbnail

        itemlist.append(item.clone(title=title,
                                   thumbnail=thumb,
                                   forcethumb=True,
                                   contentType='episode',
                                   action='play',
                                   video_id=it['guid']))

    return itemlist


def play(item):
    logger.debug()
    item.no_return=True
    mpd = config.get_setting('mpd', item.channel)


    lic_url = 'https://widevine.entitlement.theplatform.eu/wv/web/ModularDrm/getRawWidevineLicense?releasePid={pid}&account=http://access.auth.theplatform.com/data/Account/2702976343&schema=1.0&token={token}|Accept=*/*&Content-Type=&User-Agent={ua}|R{{SSM}}|'
    url = ''

    if item.urls:
        url = ''
        pid = ''
        Format = 'dash+xml' if mpd else 'x-mpegURL'
        for it in item.urls:
            if Format in it['format']:
                item.url = requests.head(it['publicUrls'][0]).headers['Location']
                pid = it['releasePids'][0]

        if mpd:
            item.manifest = 'mpd'
            item.drm = 'com.widevine.alpha'
            item.license = lic_url.format(pid=pid, token=Token, ua=support.httptools.get_user_agent())

        else:
            item.manifest = 'hls'
        return[item]

    elif item.video_id:
        payload = '{"contentId":"' + item.video_id + ' ","streamType":"VOD","delivery":"Streaming","createDevice":true}'
        res = session.post('https://api-ott-prod-fe.mediaset.net/PROD/play/playback/check/v2.0?sid=' + sid, data=payload).json()['response']['mediaSelector']

    else:
        payload = '{"channelCode":"' + item.callSign + '","streamType":"LIVE","delivery":"Streaming","createDevice":true}'
        res = session.post('https://api-ott-prod-fe.mediaset.net/PROD/play/playback/check/v2.0?sid=' + sid, data=payload).json()['response']['mediaSelector']

    url = res['url']
    mpd = True if 'dash' in res['formats'].lower() else False

    if url:

        sec_data = support.match(url + '?' + urlencode(res)).data
        item.url = support.match(sec_data, patron=r'<video src="([^"]+)').match
        pid = support.match(sec_data, patron=r'pid=([^|]+)').match

        if mpd and pid:
            item.manifest = 'mpd'
            item.drm = 'com.widevine.alpha'
            item.license = lic_url.format(pid=pid, token=Token, ua=support.httptools.get_user_agent())
        else:
            item.manifest = 'hls'

        return [item]


def get_from_id(item):
    logger.debug()
    sessionKey = session.get(sessionUrl.format(uuid=str(uuid.uuid4())), verify=False).json()['sessionKey']
    session.headers.update({'x-session': sessionKey})
    res = session.get(entry.format(id=item.args)).json()
    if 'components' in res:
        id = quote(",".join(res["components"]))
        res = session.get(entries.format(id=id)).json()
    if 'entries' in res:
        return res['entries']
    return {}

def get_programs(item, ret={}, args={}):
    url = ''
    pag = item.page if item.page else 1

    if item.feed:
        pag = item.page if item.page else 1
        url='{}&range={}-{}'.format(item.feed, pag, pag + 20 - 1)
        ret['next'] = pag + 20
        res = requests.get(url).json()

    else:
        args['uxReference'] = item.ref
        args['params'] = item.params
        args['query'] = item.query
        args['context'] = 'platform≈web'
        args['sid'] = sid
        args['sessionId'] = sid
        args['hitsPerPage'] = 20
        args['property'] = 'search' if item.query else 'play'
        args['tenant'] = 'play-prod-v2'
        args['page'] = pag
        args['deviceId'] = '017ac511182d008322c989f3aac803083002507b00bd0'
        url="https://api-ott-prod-fe.mediaset.net/PROD/play/reco/anonymous/v2.0?" + urlencode(args)

        res = session.get(url).json()

    if res:
        res = res.get('response', res)
        if 'entries' in res:
            ret['items'] = res['entries']
        elif 'blocks' in res:
            items = []
            for block in res['blocks']:
                items += block['items']
            ret['items'] = items
        if not 'next' in ret:
            next = res.get('pagination',{}).get('hasNextPage', False)
            ret['next'] = pag + 1 if next else 0
    return ret






