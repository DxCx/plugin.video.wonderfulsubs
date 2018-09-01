from resources.lib.ui import control
from resources.lib.ui import utils
from resources.lib.ui.SourcesList import SourcesList
from resources.lib.ui.router import on_param, route, router_process
from resources.lib.WonderfulSubsBrowser import WonderfulSubsBrowser
import urlparse

MENU_ITEMS = [
    (control.lang(30000), "all"),
    (control.lang(30001), "latest"),
    (control.lang(30002), "popular"),
    (control.lang(30003), "search_history"),
    (control.lang(30004), "settings"),
]

HISTORY_KEY = "addon.history"
HISTORY_DELIM = ":_:"

_BROWSER = WonderfulSubsBrowser()
control.setContent('tvshows');

def sortResultsByRes(fetched_urls):
    prefereResSetting = utils.parse_resolution_of_source(control.getSetting('prefres'))

    filtered_urls = filter(lambda x: utils.parse_resolution_of_source(x[0]) <=
                           prefereResSetting, fetched_urls)

    return sorted(filtered_urls, key=lambda x:
                  utils.parse_resolution_of_source(x[0]),
                  reverse=True)

@route('settings')
def SETTINGS(payload, params):
    return control.settingsMenu();

@route('animes/*')
def ANIMES_PAGE(payload, params):
    animeurl, flavor = payload.rsplit("/", 1)
    is_dubbed = True if "dub" == flavor else False

    order = control.getSetting('reverseorder')
    episodes = _BROWSER.get_anime_episodes(animeurl, is_dubbed)
    if ( "Ascending" in order ):
        episodes = reversed(episodes)
    return control.draw_items(episodes)

@route('all')
def LATEST(payload, params):
    return control.draw_items(_BROWSER.get_all())

@route('all/*')
def LATEST_PAGES(payload, params):
    return control.draw_items(_BROWSER.get_all(int(payload)))

@route('latest')
def LATEST(payload, params):
    return control.draw_items(_BROWSER.get_latest())

@route('latest/*')
def LATEST_PAGES(payload, params):
    return control.draw_items(_BROWSER.get_latest(int(payload)))

@route('popular')
def POPSUBBED(payload, params):
    return control.draw_items(_BROWSER.get_popular())

@route('popular/*')
def POPSUBBED_PAGES(payload, params):
    return control.draw_items(_BROWSER.get_popular(int(payload)))

@route('search_history')
def SEARCH_HISTORY(payload, params):
    history = control.getSetting(HISTORY_KEY)
    history_array = history.split(HISTORY_DELIM)
    if history != "" and "Yes" in control.getSetting('searchhistory') :
        return control.draw_items(_BROWSER.search_history(history_array))
    else :
        return SEARCH(payload,params)

@route('clear_history')
def CLEAR_HISTORY(payload, params):
    control.setSetting(HISTORY_KEY, "")
    return LIST_MENU(payload, params)

@route('search')
def SEARCH(payload, params):
    query = control.keyboard(control.lang(30003))
    if not query:
        return False

    # TODO: Better logic here, maybe move functionatly into router?
    if "Yes" in control.getSetting('searchhistory') :
        history = control.getSetting(HISTORY_KEY)
        if history != "" :
            query = query+HISTORY_DELIM
        history=query+history
        while history.count(HISTORY_DELIM) > 6 :
            history=history.rsplit(HISTORY_DELIM, 1)[0]
        control.setSetting(HISTORY_KEY, history)

    return control.draw_items(_BROWSER.search_site(query))

@route('search/*')
def SEARCH_PAGES(payload, params):
    query, page = payload.rsplit("/", 1)
    return control.draw_items(_BROWSER.search_site(query, int(page)))

@route('play/*')
def PLAY(payload, params):
    anime_url, episode = payload.rsplit("/", 1)
    anime_url, flavor = anime_url.rsplit("/", 1)
    is_dubbed = True if "dub" == flavor else False
    sources = _BROWSER.get_episode_sources(anime_url, is_dubbed, episode)
    autoplay = True if 'true' in control.getSetting('autoplay') else False

    s = SourcesList(sources.items(), autoplay, sortResultsByRes, {
        'title': control.lang(30100),
        'processing': control.lang(30101),
        'choose': control.lang(30102),
        'notfound': control.lang(30103),
    })

    return control.play_source(s.get_video_link())

@route('')
def LIST_MENU(payload, params):
    return control.draw_items(
        [utils.allocate_item(name, url, True, '') for name, url in MENU_ITEMS]
    )

router_process(control.get_plugin_url(), control.get_plugin_params())
