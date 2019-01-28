import itertools
import json
import requests
from WatchlistFlavorBase import WatchlistFlavorBase

class KitsuWLF(WatchlistFlavorBase):
    _TITLE = "Kitsu"
    _NAME = "kitsu"
    _IMAGE = "https://canny.io/images/13895523beb5ed9287424264980221d4.png"

    def login(self):
        r = requests.post('https://kitsu.io/api/oauth/token', params={
            "grant_type": "password",
            "username": self._username,
            "password": self._password
        })

        if r.status_code != 200:
            return

        data = json.loads(r.text)
        user_res = requests.get('https://kitsu.io/api/edge/users?filter[self]=true',
                                headers=self.header(data['access_token']))

        data2 = json.loads(user_res.text)["data"][0]

        return self._format_login_data((data2["attributes"]["name"]),
                                       '',
                                       ('%s/%s' % (data2['id'], data['access_token'])))

    def header(self, token):
        header = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': "Bearer {}".format(token),
            }

        return header

    def watchlist(self):
        _id, token = self._login_token.rsplit("/", 1)
        headers = self.header(token)
        params = {"filter[user_id]": _id}
        url = "https://kitsu.io/api/edge/library-entries"
        return self._process_watchlist_status_view(url, params, headers, "watchlist/%d", page=1)

    def _base_watchlist_status_view(self, res):
        base = {
            "name": res.capitalize(),
            "url": 'watchlist_status_type/'+res,
            "image": '',
            "plot": '',
        }

        return self._parse_view(base)

    def _process_watchlist_status_view(self, url, params, headers, base_plugin_url, page):
        result = requests.get(url, params=params, headers=headers).text
        results = json.loads(result)["meta"]["statusCounts"]
        all_results = map(self._base_watchlist_status_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def get_watchlist_status(self, status):
        if status == "onHold":
            status = "on_hold"

        _id, token = self._login_token.rsplit("/", 1)
        headers = self.header(token)
        url = "https://kitsu.io/api/edge/library-entries"

        params = {
            "fields[anime]": "slug,posterImage,canonicalTitle,titles,synopsis,subtype,startDate,status,averageRating,popularityRank,ratingRank,episodeCount",
            "fields[users]": "id",
            "filter[user_id]": _id,
            "filter[kind]": "anime",
            "filter[status]": status,
            "include": "anime,user,mediaReaction",
            "page[limit]": "500",
            "page[offset]": "0",
            "sort": "anime.titles.canonical",
            }

        return self._process_watchlist_view(url, params, headers, "watchlist/%d", page=1)

    def _process_watchlist_view(self, url, params, headers, base_plugin_url, page):
        result = requests.get(url, params=params, headers=headers).text
        results = json.loads(result)["included"][1:]
        results2 = json.loads(result)["data"]
        all_results = map(self._base_watchlist_view, results, results2)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_view(self, res, res2):
        base = {
            "name": '%s - %d/%d' % (res["attributes"]['canonicalTitle'],
                                    res2["attributes"]['progress'],
                                    res["attributes"]['episodeCount'] if res["attributes"]['episodeCount'] is not None else 0),
            "url": "watchlist_query/%s/%s" % (res["attributes"]['canonicalTitle'], res["id"]),
            "image": res["attributes"]['posterImage']['medium'],
            "plot": res["attributes"]["synopsis"],
        }

        return self._parse_view(base)

