# -*- coding: utf-8 -*-
import sys
import xbmc
from xbmcgui import Dialog
import xbmcaddon
from os.path import join, isfile
from codecs import open as codecs_open
from json import loads
from datetime import datetime as dt
from service import addon, LANG, addonname, encode, decode
from service import PY3, dictfile, jsonrequest, log, notify

base_url = "https://api.mujrozhlas.cz/"

if isfile(dictfile):
    f = codecs_open(dictfile, 'r', encoding = "utf-8")
    data = f.read()
    chann_dict = loads(data)
    f.close()

def okdialog(message):
    if PY3:
        return Dialog().ok(heading=addonname, message = message)
    return Dialog().ok(heading=addonname, line1 = message)

def getNumbers(txt):
    newstr = ''.join((ch if ch in '0123456789' else ' ') for ch in txt)
    return [int(i) for i in newstr.split()]

# it must not depend on the user's date and time format settings !
def parsedatetime(_short, _long):
    ix = _short.find(' ')
    lnums = getNumbers(_long)
    snums = getNumbers(_short[:ix])
    year = max(lnums)
    day = min(lnums)
    snums.remove(day)
    month = min(snums)
    return '%i-%02d-%02d' % (year, month, day)

def getepisodes(showid, offset, limit = 1):
    url = base_url+'shows/%s/episodes?page[limit]=%i&page[offset]=%i' % (showid, limit, offset)
    return jsonrequest(url)

def getcount(showid):
    ep = getepisodes(showid, 0)
    if ep:
        if 'meta' in ep and 'count' in ep['meta']:
            return ep['meta']['count']
    return 0

def getep(showid, since):
    count = getcount(showid)
    if count:
        res = []
        resb = []
#        resc = []
        limit = 30
        #sinceb = since[:-3]
        #sincec = since[:-6]
        since = since[:-3]
        sinceb = since[:-6]
        for i in range(0, count, limit):
            epdata = getepisodes(showid, i, limit)
            if 'data' in epdata:
                data = epdata['data']
                for itm in data:
                    #_since = itm['attributes']['since'][:-9]
                    _since = itm['attributes']['since'][:-12]
                    if _since == since:
                        res.append(itm)
                    if _since[:-3] == sinceb:
                        resb.append(itm)
#                    if _since[:-6] == sincec:
#                        resc.append(itm)
        if res:
            log("res = " + repr(res))
            return res
        if resb:
            log("resb =" + repr(resb))
            return resb
#        if resc:
#            log("resc =" + repr(resc))
#            return resc
        return ''

    else:
        log("Count is none or 0")

def getshows(statid, limit, offset):
    url = base_url+'stations/%s/shows?page[limit]=%i&page[offset]=%i' % (statid, limit, offset)
    return jsonrequest(url)

def findshowid(statid, title):
    count = 0
    first = getshows(statid, 1, 0)
    if first is not None:
        if 'meta' in first and 'count' in first['meta']:
            count = first['meta']['count']
    if count:
        limit = 30
        for i in range(0, count, limit):
            showdata = getshows(statid, limit, i)
            if 'data' in showdata:
                data = showdata['data']
                for itm in data:
                    if 'attributes' in itm and 'title' in itm['attributes'] and 'id' in itm:
                        _title = itm['attributes']['title']
                        if _title == title:
                            return itm['id']
    return ''

def get_audio(kind):
    if sys.listitem.getPath() != xbmc.getInfoLabel('ListItem.FolderPath'):
        okdialog(LANG(30402))
        return
    label = xbmc.getInfoLabel('ListItem.Label')
    log("label = "+repr(label))
    plot = xbmc.getInfoLabel('ListItem.Plot')
    icon = xbmc.getInfoLabel('ListItem.Icon')
    channel = xbmc.getInfoLabel('ListItem.ChannelName')
    starttime = xbmc.getInfoLabel('ListItem.StartTime')
    statid = None
    if decode(channel) in chann_dict:
        statid = decode(chann_dict[decode(channel)])
    if statid is not None:
        day = parsedatetime(xbmc.getInfoLabel('ListItem.Date'), xbmc.getInfoLabel('ListItem.StartDate'))
        starttime = starttime if len(starttime) == 5 else '0' + starttime
        since = '%sT%s' % (day, starttime)
        log("since = " + repr(since))
        url = base_url + 'schedule-day?filter[day]=' + day + '&filter[stations.id]=' + statid
        data = jsonrequest(url)
        if data is not None and 'links' in data:
            links = data['links']
            if 'next' in links and links['next'] == None:
                if 'data' in data:
                    data = data['data']
                    ep1a = [i for i in data if i['attributes']['since'][:-9] == since and encode(i['attributes']['mirroredShow']['title']) == label]
                    ep2a = [i for i in data if i['attributes']['since'][:-12] == since[:-3] and encode(i['attributes']['mirroredShow']['title']) == label]
                    ep3a = [i for i in data if i['attributes']['since'][:-15] == since[:-6] and encode(i['attributes']['mirroredShow']['title']) == label]
                    ep1b = [i for i in data if i['attributes']['since'][:-9] == since and encode(i['attributes']['title']) == label]
                    ep2b = [i for i in data if i['attributes']['since'][:-12] == since[:-3] and encode(i['attributes']['title']) == label]
                    ep3b = [i for i in data if i['attributes']['since'][:-15] == since[:-6] and encode(i['attributes']['title']) == label]
                    ep = ep1a if ep1a else ep1b if ep1b else ep2a if ep2a else ep2b if ep2b else ep3a if ep3a else ep3b
                    if len(ep) > 1:
                        notify(LANG(30410))
                    ep = ep[0] if len(ep) else None
                    if isinstance(ep, dict):
                        log("scheduled episode  = " + repr(ep))
                        if 'attributes' in ep:
                            till = ep['attributes']['till'][:-6]
                            nowd = xbmc.getInfoLabel('System.Date(yyyy-mm-dd)')
                            nowt = xbmc.getInfoLabel('System.Time(hh:mm)')
                            now = '%sT%s' % (nowd, nowt)
                            if till >= now:
                                notify(LANG(30401))
                                return
                            #show = ep['relationships']['show']
                            show = ep['attributes']['mirroredShow']
                            if 'data' in show and 'id' in show['data']:
                                showid = show['data']['id']
                            else: # must be searched by aired show title
                                log("show id not in show['data'] or 'data' not in response")
                                showid = ''
                                title = ep['attributes']['mirroredShow']['title']
                                log("mirroredShow title  = " + title)
                                showid = findshowid(statid, title)
                                if not showid:
                                    title = ep['attributes']['title']
                                    log("title  = " + title)
                                    showid = findshowid(statid, title)
                        else:
                            notify(LANG(30405))
                            return
                        if showid:
                            log("showid = " + showid)
                            epis = getep(showid, since)
                            if epis is None:
                                notify(LANG(30404))
                                return
                            if epis:
                                res = []
                                for epi in epis:
                                    log("epi = "+repr(epi))
                                    if 'attributes' in epi:
                                        part = total = 0
                                        attrs = epi['attributes']
                                        if len(epis) > 1:
                                            descr = attrs['description'].replace('<p>','').replace('</p>','').replace('&nbsp;',' ')
                                            title = attrs['title']
                                            if 'part' in attrs and 'mirroredSerial' in attrs and 'totalParts' in attrs['mirroredSerial']:
                                                part = attrs['part']
                                                total = attrs['mirroredSerial']['totalParts']
                                        else:
                                            descr = plot
                                            title = label
                                        if 'asset' in attrs and 'url' in attrs['asset'] and attrs['asset']['url']:
                                            icon = attrs['asset']['url']
                                        if 'audioLinks' in attrs:
                                            al = attrs['audioLinks'][0]
                                            if len(al):
                                                if kind == 'down' and 'playableTill' in al:
                                                    notify(LANG(30409))
                                                    return
                                                link = attrs['audioLinks'][0]['url']
                                                res.append((link, title, attrs['since'][:-9].replace('T', ' '), descr, part, total))
                                res.sort(key = lambda x:(x[1], x[4]))
                                log("result = "+repr(res))
                                return [label, channel, icon, res]
                            else:
                                notify(LANG(30403))
                        else:
                            notify(LANG(30404))
                    else:
                        notify(LANG(30403))
            else:
                log("################  paging ? ################")
        else:
            log("############## 'links' not in data or data is None ##############")
    else:
        log("############ unknown id of station ############")
    return
