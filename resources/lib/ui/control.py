import re
import sys
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import http
import urlparse

try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

HANDLE=int(sys.argv[1])
ADDON_NAME = re.findall('plugin:\/\/([\w\d\.]+)\/', sys.argv[0])[0]
__settings__ = xbmcaddon.Addon(ADDON_NAME)
__language__ = __settings__.getLocalizedString
CACHE = StorageServer.StorageServer("%s.animeinfo" % ADDON_NAME, 24)

class hook_mimetype(object):
    __MIME_HOOKS = {}

    @classmethod
    def trigger(cls, mimetype, item):

        if mimetype in cls.__MIME_HOOKS.keys():
            return cls.__MIME_HOOKS[mimetype](item)

        return item

    def __init__(self, mimetype):
        self._type = mimetype

    def __call__(self, func):
        assert self._type not in self.__MIME_HOOKS.keys()
        self.__MIME_HOOKS[self._type] = func
        return func

class watchlistPlayer(xbmc.Player):

    def __init__(self):
        super(watchlistPlayer, self).__init__()
        self._on_playback_done = None
        self._on_stopped = None
        self._on_percent = None

    def handle_player(self, on_playback_done, on_stopped, on_percent):
        if not on_playback_done:
            return

        self._on_playback_done = on_playback_done
        self._on_stopped = on_stopped
        self._on_percent = on_percent
        self.keepAlive()
        
    def onPlayBackStarted(self):
        pass

    def onPlayBackStopped(self):
        if not self._on_stopped():
            return

        self._on_playback_done()

    def onPlayBackEnded(self):
        self._on_playback_done()

    def getWatchedPercent(self):
        watched_percent = 0
        current_time = self.getTime()
        media_length = self.getTotalTime()

        if int(media_length) is not 0:
            watched_percent = float(current_time) / float(media_length) * 100

        return watched_percent

    def onWatchedPercent(self):
        while self.isPlaying():
            xbmc.sleep(5000)
            if self.getWatchedPercent() > self._on_percent():
                self._on_playback_done()
                break

    def keepAlive(self):
        for i in range(0, 240):
            if self.isPlayingVideo(): break
            xbmc.sleep(1000)

        if self._on_percent:
            return self.onWatchedPercent()

        while self.isPlaying():
            xbmc.sleep(5000)

def refresh():
    return xbmc.executebuiltin('Container.Refresh')

def settingsMenu():
    return xbmcaddon.Addon().openSettings()

def getSetting(key):
    return __settings__.getSetting(key)

def setSetting(id, value):
    return __settings__.setSetting(id=id, value=value)

def cache(funct, *args):
    return CACHE.cacheFunction(funct, *args)

def lang(x):
    return __language__(x).encode('utf-8')

def addon_url(url=''):
    return "plugin://%s/%s" % (ADDON_NAME, url)

def get_plugin_url():
    addon_base = addon_url()
    assert sys.argv[0].startswith(addon_base), "something bad happened in here"
    return sys.argv[0][len(addon_base):]

def get_plugin_params():
    return dict(urlparse.parse_qsl(sys.argv[2].replace('?', '')))

def keyboard(text):
    keyboard = xbmc.Keyboard("", text, False)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText()
    return None

def ok_dialog(title, text):
    return xbmcgui.Dialog().ok(title, text)

def yesno_dialog(title, text, nolabel=None, yeslabel=None):
    return xbmcgui.Dialog().yesno(title, text, nolabel=nolabel, yeslabel=yeslabel)

def multiselect_dialog(title, _list):
    if isinstance(_list, list):
        return xbmcgui.Dialog().multiselect(title, _list)
    return None

def xbmc_add_player_item(name, url, iconimage='', description='', draw_cm=None):
    ok=True
    u=addon_url(url)
    cm = draw_cm(u) if draw_cm is not None else []

    liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo('video', infoLabels={ "Title": name, "Plot": description })
    liz.setProperty("fanart_image", __settings__.getAddonInfo('path') + "/fanart.jpg")
    liz.setProperty("Video", "true")
    liz.setProperty("IsPlayable", "true")
    liz.addContextMenuItems(cm, replaceItems=False)
    ok=xbmcplugin.addDirectoryItem(handle=HANDLE,url=u,listitem=liz, isFolder=False)
    return ok

def xbmc_add_dir(name, url, iconimage='', description='', draw_cm=None):
    ok=True
    u=addon_url(url)
    cm = draw_cm(u) if draw_cm is not None else []

    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo('video', infoLabels={ "Title": name, "Plot": description })
    liz.setProperty("fanart_image", iconimage)
    liz.addContextMenuItems(cm, replaceItems=False)
    ok=xbmcplugin.addDirectoryItem(handle=HANDLE,url=u,listitem=liz,isFolder=True)
    return ok

def _prefetch_play_link(link):
    if callable(link):
        link = link()

    if not link:
        return None

    linkInfo = http.head_request(link);
    if linkInfo.status_code != 200:
        raise Exception('could not resolve %s. status_code=%d' %
                        (link, linkInfo.status_code))
    return {
        "url": linkInfo.url,
        "headers": linkInfo.headers,
    }

def play_source(link, on_episode_done=None, on_stopped=None, on_percent=None):
    linkInfo = _prefetch_play_link(link)
    if not linkInfo:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    item = xbmcgui.ListItem(path=linkInfo['url'])
    if 'Content-Type' in linkInfo['headers']:
        item.setProperty('mimetype', linkInfo['headers']['Content-Type'])

    # Run any mimetype hook
    item = hook_mimetype.trigger(linkInfo['headers']['Content-Type'], item)
    xbmcplugin.setResolvedUrl(HANDLE, True, item)
    watchlistPlayer().handle_player(on_episode_done, on_stopped, on_percent)

def draw_items(video_data, contentType="tvshows", draw_cm=None):
    for vid in video_data:
        if vid['is_dir']:
            xbmc_add_dir(vid['name'], vid['url'], vid['image'], vid['plot'], draw_cm)
        else:
            xbmc_add_player_item(vid['name'], vid['url'], vid['image'],
                                 vid['plot'], draw_cm)
    xbmcplugin.setContent(HANDLE, contentType)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=True)
    return True

@hook_mimetype('application/dash+xml')
def _DASH_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('mpd')
    if is_helper.check_inputstream():
        item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type',
                             'mpd')
        item.setContentLookup(False)
    else:
        raise Exception("InputStream Adaptive is not supported.")

    return item

@hook_mimetype('application/vnd.apple.mpegurl')
def _HLS_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('hls')
    if is_helper.check_inputstream():
        item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type',
                             'hls')
        item.setContentLookup(False)
    else:
        raise Exception("InputStream Adaptive is not supported.")

    return item
