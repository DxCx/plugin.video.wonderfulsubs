import itertools
import json

from ..constants import API_BASE, BASE_URL
from ..ui import utils
from WatchlistFlavorBase import WatchlistFlavorBase

class WonderfulSubsWLF(WatchlistFlavorBase):
    _URL = "{}/{}".format(BASE_URL, API_BASE)
    _TITLE = "WonderfulSubs"
    _NAME = "wonderfulsubs"

    @property
    def image(self):
        return self._login_image

    def login(self):
        url = self._to_url("users/login")
        data = (self._post_request(url, json={"username": self._username, "password": self._password})).json()

        if data['success'] is not True:
            return

        return self._format_login_data((data['data']['username']),
                                       (data['data']['profile_pic']),
                                       ('%s/%s' % (data['data']['_id'], data['token'])))

    def watchlist(self):
        url = self._to_url("watchlist/list?_id=%s" % self._login_token.split("/")[0])
        return self._process_watchlist_view(url, "watchlist/%d", page=1)

    def __header(self):
        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(self._login_token.split("/")[1])
            }

        return header

    def _base_watchlist_view(self, res):
        result = []

        base = {
            "name": '%s' % (res['title']),
            "url": "animes/" + res["url"].replace("/watch/", ""),
            "image": res['poster'],
            "plot": '',
        }

        POP_FLAVOR = self.__get_sort()
        if POP_FLAVOR:
            res.pop(POP_FLAVOR)

        if res.get("is_dubbed", None):
            result.append(utils.allocate_item("%s (Dub)" % base["name"] if not POP_FLAVOR else base["name"],
                                              "%s/dub" % base["url"],
                                              True,
                                              base["image"],
                                              base["plot"]))
        if res.get("is_subbed", None):
            result.append(utils.allocate_item("%s (Sub)" % base["name"] if not POP_FLAVOR else base["name"],
                                              "%s/sub" % base["url"],
                                              True,
                                              base["image"],
                                              base["plot"]))

        return result

    def _process_watchlist_view(self, url, base_plugin_url, page):
        resp = self._get_request(url, headers=self.__header())
        results = resp.json()['data']['watch_list']
        all_results = map(self._base_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def watchlist_update(self, episode, kitsu_id):
        return False

    def __get_sort(self):
        sort_types = {
            "Subs Only": "is_dubbed",
            "Dubs Only": "is_subbed",
            "None": None
            }

        return sort_types[self._sort]
