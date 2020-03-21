from ui import control
from ui.router import route
from WatchlistFlavor import WatchlistFlavor

_BROWSER = None
_draw_cm = None


def set_browser(browser, draw_cm):
    global _BROWSER
    global _draw_cm
    _BROWSER = browser
    _draw_cm = draw_cm


@route('watchlist_login/*')
def WL_LOGIN(payload, params):
    return WatchlistFlavor.login_request(payload.rsplit("/")[0])


@route('watchlist_logout')
def WL_LOGOUT(payload, params):
    return WatchlistFlavor.logout_request()


@route('watchlist')
def WATCHLIST(payload, params):
    return control.draw_items(WatchlistFlavor.watchlist_request(), draw_cm=_draw_cm)


@route('watchlist_status_type/*')
def WATCHLIST_STATUS_TYPE(payload, params):
    return control.draw_items(WatchlistFlavor.watchlist_status_request(payload.rsplit("/")[0]), draw_cm=_draw_cm)


@route('watchlist_query/*')
def WATCHLIST_QUERY(payload, params):
    return control.draw_items(_BROWSER.search_site(payload.rsplit("/")[0]), draw_cm=_draw_cm)


def watchlist_update(episode, kitsu_id):
    flavor = WatchlistFlavor.get_active_flavor()
    if not flavor:
        return

    return WatchlistFlavor.watchlist_update_request(episode, kitsu_id)


def add_watchlist(items):
    flavor = WatchlistFlavor.get_active_flavor()
    if not flavor:
        return

    token_expired = WatchlistFlavor.check_token_expiration()
    if token_expired:
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
