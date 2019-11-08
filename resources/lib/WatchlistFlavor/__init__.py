from time import time
from ..ui import control
from WatchlistFlavorBase import WatchlistFlavorBase

import MyAnimeList
import WonderfulSubs
import Kitsu
import AniList

class WatchlistFlavor(object):
    __LOGIN_KEY = "addon.login"
    __LOGIN_FLAVOR_KEY = "%s.flavor" % __LOGIN_KEY
    __LOGIN_NAME_KEY = "%s.name" % __LOGIN_KEY
    __LOGIN_IMAGE_KEY = "%s.image" % __LOGIN_KEY
    __LOGIN_TOKEN_KEY = "%s.token" % __LOGIN_KEY
    __LOGIN_TS_KEY = "%s.ts" %__LOGIN_KEY

    __SELECTED = None

    def __init__(self):
        raise Exception("Static Class should not be created")

    @staticmethod
    def get_active_flavor():
        selected = control.getSetting(WatchlistFlavor.__LOGIN_FLAVOR_KEY)
        if not selected:
            return None

        if not WatchlistFlavor.__SELECTED:
            WatchlistFlavor.__SELECTED = \
                    WatchlistFlavor.__instance_flavor(selected)

        return WatchlistFlavor.__SELECTED

    @staticmethod
    def check_token_expiration():
        login_ts = control.getSetting(WatchlistFlavor.__LOGIN_TS_KEY)
        if not login_ts:
            return True

        expires_in = 2591963 # Seconds until the access_token expires (30 days)
        expires_ts = int(login_ts) + expires_in
        if expires_ts <= int(time()):
            control.ok_dialog(control.lang(30400), control.lang(30403))
            return True

        return False

    @staticmethod
    def watchlist_request():
        return WatchlistFlavor.get_active_flavor().watchlist()

    @staticmethod
    def watchlist_status_request(status):
        return WatchlistFlavor.get_active_flavor().get_watchlist_status(status)

    @staticmethod
    def watchlist_update_request(episode, kitsu_id):
        return WatchlistFlavor.get_active_flavor().watchlist_update(episode, kitsu_id)

    @staticmethod
    def login_request(flavor):
        if not WatchlistFlavor.__is_flavor_valid(flavor):
            raise Exception("Invalid flavor %s" % flavor)

        flavor_class = WatchlistFlavor.__instance_flavor(flavor)
        login_ts = int(time())

        return WatchlistFlavor.__set_login(flavor,
                                           flavor_class.login(),
                                           str(login_ts)
                                           )

    @staticmethod
    def logout_request():
        control.setSetting(WatchlistFlavor.__LOGIN_FLAVOR_KEY, '')
        control.setSetting(WatchlistFlavor.__LOGIN_NAME_KEY, '')
        control.setSetting(WatchlistFlavor.__LOGIN_IMAGE_KEY, '')
        control.setSetting(WatchlistFlavor.__LOGIN_TOKEN_KEY, '')
        control.setSetting(WatchlistFlavor.__LOGIN_TS_KEY, '')
        return control.refresh()

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
    def __instance_flavor(name):
        login_name = control.getSetting(WatchlistFlavor.__LOGIN_NAME_KEY)
        login_token = control.getSetting(WatchlistFlavor.__LOGIN_TOKEN_KEY)
        login_image = control.getSetting(WatchlistFlavor.__LOGIN_IMAGE_KEY)
        username = control.getSetting('%s.name' % name)
        password = control.getSetting('%s.password' % name)
        sort = control.getSetting('%s.sort' % name)
        title_lang = control.getSetting('%s.titles' % name)

        flavor_class = WatchlistFlavor.__get_flavor_class(name)
        return flavor_class(login_name, username, password, login_image, login_token, sort, title_lang)

    @staticmethod
    def __set_login(flavor, res, login_ts):
        if not res:
            return control.ok_dialog(control.lang(30400), control.lang(30401))

        control.setSetting(WatchlistFlavor.__LOGIN_FLAVOR_KEY, flavor)
        control.setSetting(WatchlistFlavor.__LOGIN_TS_KEY, login_ts)
        control.setSetting(WatchlistFlavor.__LOGIN_TOKEN_KEY, res['token'])
        control.setSetting(WatchlistFlavor.__LOGIN_IMAGE_KEY, res['image'])
        control.setSetting(WatchlistFlavor.__LOGIN_NAME_KEY, res['name'])
        control.refresh()
        return control.ok_dialog(control.lang(30400), control.lang(30402))
