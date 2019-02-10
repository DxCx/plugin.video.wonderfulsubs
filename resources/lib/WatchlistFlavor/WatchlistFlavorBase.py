import requests
from ..ui import utils

class WatchlistFlavorBase(object):
    _URL = None
    _TITLE = None
    _NAME = None
    _IMAGE = None

    def __init__(self, login_name, username, password, login_image, login_token, sort, title_lang):
        if type(self) is WatchlistFlavorBase:
            raise Exception("Base Class should not be created")

        self._login_name = login_name
        self._username = username
        self._password = password
        self._login_image = login_image
        self._login_token = login_token
        self._sort = sort
        self._title_lang = title_lang

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
    def url(self):
        if self._URL is None:
            raise Exception("Missing Url")

        return self._URL

    @property
    def login_name(self):
        return self._login_name

    def login(self):
        raise NotImplementedError("login should be implemented by subclass")

    def watchlist(self):
        raise NotImplementedError("watchlist should be implemented by subclass")

    def get_watchlist_status(self, status):
        raise NotImplementedError("get_watchlist_status should be implemented by subclass")

    def watchlist_update(self):
        raise NotImplementedError("watchlist_update should be implemented by subclass")

    def _format_login_data(self, name, image, token):
        login_data = {
            "name": name,
            "image": image,
            "token": token,
            }

        return login_data

    def _parse_view(self, base):
        return [
            utils.allocate_item("%s" % base["name"],
                                base["url"],
                                True,
                                base["image"],
                                base["plot"])
            ]

    def _to_url(self, url=''):
        if url.startswith("/"):
            url = url[1:]
        return "%s/%s" % (self._URL, url)

    def _send_request(self, url, headers=None, cookies=None, data=None, params=None):
        return requests.get(url, headers=headers, cookies=cookies, data=data, params=params).text

    def _post_request(self, url, headers=None, cookies=None, params=None, json=None):
        return requests.post(url, headers=headers, cookies=cookies, params=params, json=json)

    def _patch_request(self, url, headers=None, cookies=None, params=None, json=None):
        return requests.patch(url, headers=headers, cookies=cookies, params=params, json=json)
