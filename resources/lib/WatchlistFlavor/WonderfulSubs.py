import itertools
import json
import requests
from ..ui import utils
from WatchlistFlavorBase import WatchlistFlavorBase

class WonderfulSubsWLF(WatchlistFlavorBase):
    _TITLE = "WonderfulSubs"
    _NAME = "wonderfulsubs"

    @property
    def image(self):
        return self._login_image

    def login(self):
        r = requests.post('https://www.wonderfulsubs.com/api/users/login',
                          json={"username": self._username, "password": self._password})

        data = json.loads(r.text)

        if data['success'] is not True:
            return

        return self._format_login_data((data['data']['username']),
                                       (data['data']['profile_pic']),
                                       ('%s/%s' % (data['data']['_id'], data['token'])))

    def watchlist(self):
        url = 'https://www.wonderfulsubs.com/api/watchlist/list?_id=%s' % (self._login_token.split("/")[0])
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

        if res["is_dubbed"]:
            result.append(utils.allocate_item("%s (Dub)" % base["name"],
                                              "%s/dub" % base["url"],
                                              True,
                                              base["image"],
                                              base["plot"]))
        if res["is_subbed"]:
            result.append(utils.allocate_item("%s (Sub)" % base["name"],
                                              "%s/sub" % base["url"],
                                              True,
                                              base["image"],
                                              base["plot"]))

        return result

    def _process_watchlist_view(self, url, base_plugin_url, page):
        r = requests.get(url, headers=self.__header())
        results = json.loads(r.text)['data']['watch_list']
        all_results = map(self._base_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results
