from ui import control
from ui.router import route
from WatchlistFlavor import WatchlistFlavor

_BROWSER = None
def set_browser(browser):
    global _BROWSER
    _BROWSER = browser

@route('watchlist_login/*')
def WL_LOGIN(payload, params):
    return WatchlistFlavor.login_request(payload.rsplit("/")[0])

@route('watchlist_logout')
def WL_LOGOUT(payload, params):
    return WatchlistFlavor.logout_request()

@route('watchlist')
def WATCHLIST(payload, params):
    return control.draw_items(WatchlistFlavor.watchlist_request())

@route('watchlist_status_type/*')
def WATCHLIST_STATUS_TYPE(payload, params):
    return control.draw_items(WatchlistFlavor.watchlist_status_request(payload.rsplit("/")[0]))

@route('watchlist_query/*')
def WATCHLIST_QUERY(payload, params):
    return control.draw_items(_BROWSER.search_site(payload.rsplit("/")[0]))

def watchlist_update(episode, kitsu_id):
    flavor = WatchlistFlavor.get_active_flavor()
    if not flavor:
        return

    return WatchlistFlavor.watchlist_update_request(episode, kitsu_id)

def add_watchlist(items):
    flavor = WatchlistFlavor.get_active_flavor()
    if not flavor:
        return

    items.insert(0, (
        "%s's %s" % (flavor.login_name, flavor.title),
        "watchlist",
        flavor.image,
    ))

    items.insert(len(items), (
        "Logout",
        "watchlist_logout",
        ''
    ))
