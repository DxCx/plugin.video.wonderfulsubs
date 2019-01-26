from collections import defaultdict
from ui import control
from ui.router import on_param, route, router_process
from WatchListFlavorBrowser import AuthToken, WatchList

LOGIN_KEY = "addon.login"
LOGIN_FLAVOR_KEY = "%s.flavor" % LOGIN_KEY
LOGIN_NAME_KEY = "%s.name" % LOGIN_KEY
LOGIN_IMAGE_KEY = "%s.image" % LOGIN_KEY
LOGIN_TOKEN_KEY = "%s.token" % LOGIN_KEY

class WatchlistFlavorBase(object):
    _TITLE = None
    _NAME = None
    _IMAGE = None

    def __init__(self):
        if isinstance(self, WatchlistFlavor):
            raise Exception("Base Class should not be created")

    @classmethod
    def name(cls):
        if cls._NAME is None:
            raise Exception("Missing Name")

        return cls._NAME

    @property
    def image(self):
        if self._IMAGE is None:
            raise Exception("Missing Image")

        return self._IMAGE

    @property
    def title(self):
        if self._TITLE is None:
            raise Exception("Missing Title")

        return self._TITLE

    @property
    def login_name(self):
        return control.getSetting(LOGIN_NAME_KEY)

    @property
    def login_token(self):
        return control.getSetting(LOGIN_TOKEN_KEY)

    def login(self):
        # TODO: Should implement child classes for each Auth Token.
        # TODO: Login should return formated dictionary of {'name', 'image',
        # 'token'}
        login_method = getattr(AuthToken(), self.name() + '_login')
        username = control.getSetting('%s.name' % (self.name()))
        password = control.getSetting('%s.password' % (self.name()))
        return login_method(username, password)

class WatchlistFlavor(object):
    _SELECTED = None

    @staticmethod
    def __get_flavor_class(name):
        for flav in WatchlistFlavorBase.__subclasses__():
            if flav.name() == name:
                return flav
        return None

    @staticmethod
    def __is_flavor_valid(name):
        return WatchlistFlavor.__get_flavor_class(name) != None

    @staticmethod
    def get_active_flavor():
        selected = control.getSetting(LOGIN_FLAVOR_KEY)
        if not selected:
            return None

        if not WatchlistFlavor._SELECTED:
            WatchlistFlavor._SELECTED = \
                    WatchlistFlavor.__get_flavor_class(selected)()

        return WatchlistFlavor._SELECTED

    @staticmethod
    def login_request(flavor):
        if not WatchlistFlavor.__is_flavor_valid(flavor):
            raise Exception("Invalid flavor %s" % flavor)

        flavor = WatchlistFlavor.__get_flavor_class(flavor)()
        return WatchlistFlavor.__set_login(flavor,
                                           flavor.login())

    @staticmethod
    def __set_login(flavor, res):
        if not res:
            return control.ok_dialog('Login', 'Incorrect username or password')

        control.setSetting(LOGIN_FLAVOR_KEY, flavor)
        control.setSetting(LOGIN_TOKEN_KEY, res['token'])
        control.setSetting(LOGIN_IMAGE_KEY, res['image'])
        control.setSetting(LOGIN_NAME_KEY, res['name'])
        control.refresh()

    @staticmethod
    def logout_request():
        control.setSetting(LOGIN_FLAVOR_KEY, '')
        control.setSetting(LOGIN_NAME_KEY, '')
        control.setSetting(LOGIN_IMAGE_KEY, '')
        control.setSetting(LOGIN_TOKEN_KEY, '')
        control.refresh()

    def __init__(self):
        raise Exception("Static Class should not be created")

# TODO: Move into thier own files, Base class should be its own file too,
# Each file imports from this base class.
class MyAnimeListWLF(WatchlistFlavorBase):
    _TITLE = "MyAnimeList"
    _NAME = "mal"
    _IMAGE = "https://myanimelist.cdn-dena.com/images/mal-logo-xsmall@2x.png?v=160803001"

class AniListWLF(WatchlistFlavorBase):
    _TITLE = "AniList"
    _NAME = "anilist"
    _IMAGE = "https://blobscdn.gitbook.com/v0/b/gitbook-28427.appspot.com/o/spaces%2F-LHizcWWtVphqU90YAXO%2Favatar.png?generation=1531944291782256&alt=media"

class KitsuWLF(WatchlistFlavorBase):
    _TITLE = "Kitsu"
    _NAME = "kitsu"
    _IMAGE = "https://canny.io/images/13895523beb5ed9287424264980221d4.png"

class WonderfulSubsWLF(WatchlistFlavorBase):
    _TITLE = "WonderfulSubs"
    _NAME = "wonderfulsubs"

    @property
    def image(self):
        return control.getSetting(LOGIN_IMAGE_KEY)

@route('watchlist_login/*')
def WL_LOGIN(payload, params):
    return WatchlistFlavor.login_request(payload.rsplit("/")[0])

@route('watchlist_logout')
def WL_LOGOUT(payload, params):
    return WatchlistFlavor.logout_request()

# TODO: one route of watch list.
# get_active_flavor and call a function of flavor.
@route('watchlist/*')
def WATCHLIST(payload, params):
    flavor = payload.rsplit("/")[0]
    return control.draw_items((getattr(WatchList(), flavor+'_watchlist')(control.getSetting(LOGIN_TOKEN_KEY), control.getSetting(LOGIN_NAME_KEY))))

@route('watchlist_flavor/kitsu/*')
def KITSU_LIST(payload, params):
    status = payload.rsplit("/")[1]
    return control.draw_items(WatchList().get_kitsu_watchlist_status(control.getSetting(LOGIN_TOKEN_KEY), status))

@route('watchlist_flavor/mal/*')
def MAL_LIST(payload, params):
    status = payload.rsplit("/")[0]
    return control.draw_items(WatchList().get_mal_watchlist_status(control.getSetting(LOGIN_NAME_KEY), status))

@route('watchlist_query/*')
def WATCHLIST_QUERY(payload, params):
    query, _id = payload.rsplit("/", 1)
    return control.draw_items(_BROWSER.search_site(query))
# End of above TODO

def add_watchlist(items):
    flavor = WatchlistFlavor.get_active_flavor()
    if not flavor:
        return

    items.insert(0, (
        "%s's %s" %(flavor.login_name,
                    flavor.title),
        "watchlist",
        flavor.image,
    ))

    items.insert(len(items), (
        "Logout",
        "watchlist_logout",
        ''
    ))
