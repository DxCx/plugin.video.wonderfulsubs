import itertools
import json
from WatchlistFlavorBase import WatchlistFlavorBase

class KitsuWLF(WatchlistFlavorBase):
    _URL = "https://kitsu.io/api"
    _TITLE = "Kitsu"
    _NAME = "kitsu"
    _IMAGE = "https://canny.io/images/13895523beb5ed9287424264980221d4.png"

    def login(self):
        params = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password
            }
        resp = self._post_request(self._to_url("oauth/token"), params=params)

        if resp.status_code != 200:
            return

        data = json.loads(resp.text)
        data2 = json.loads(self._send_request(self._to_url("edge/users?filter[self]=true"), headers=self.__header(data['access_token'])))["data"][0]

        return self._format_login_data((data2["attributes"]["name"]),
                                       '',
                                       ('%s/%s' % (data2['id'], data['access_token'])))

    def __header(self, token):
        header = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': "Bearer {}".format(token),
            }

        return header

    def watchlist(self):
        _id, token = self._login_token.rsplit("/", 1)
        headers = self.__header(token)
        params = {"filter[user_id]": _id}
        url = self._to_url("edge/library-entries")
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
        result = self._send_request(url, headers=headers, params=params)
        results = json.loads(result)["meta"]["statusCounts"]
        all_results = map(self._base_watchlist_status_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def get_watchlist_status(self, status):
        if status == "onHold":
            status = "on_hold"

        _id, token = self._login_token.rsplit("/", 1)
        headers = self.__header(token)
        url = self._to_url("edge/library-entries")

        params = {
            "fields[anime]": "slug,posterImage,canonicalTitle,titles,synopsis,subtype,startDate,status,averageRating,popularityRank,ratingRank,episodeCount",
            "fields[users]": "id",
            "filter[user_id]": _id,
            "filter[kind]": "anime",
            "filter[status]": status,
            "include": "anime,user,mediaReaction",
            "page[limit]": "500",
            "page[offset]": "0",
            "sort": self.__get_sort(),
            }

        return self._process_watchlist_view(url, params, headers, "watchlist/%d", page=1)

    def _process_watchlist_view(self, url, params, headers, base_plugin_url, page):
        result = json.loads(self._send_request(url, headers=headers, params=params))
        results = result["included"][1:]
        results2 = result["data"]
        all_results = map(self._base_watchlist_view, results, results2)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_view(self, res, res2):
        base = {
            "name": '%s - %d/%d' % (res["attributes"]["titles"].get(self.__get_title_lang(), res["attributes"]['canonicalTitle']),
                                    res2["attributes"]['progress'],
                                    res["attributes"]['episodeCount'] if res["attributes"]['episodeCount'] is not None else 0),
            "url": "watchlist_query/%s/%s" % (res["attributes"]['canonicalTitle'], res["id"]),
            "image": res["attributes"]['posterImage']['medium'],
            "plot": res["attributes"]["synopsis"],
        }

        return self._parse_view(base)

    def watchlist_update(self, episode, kitsu_id):
        uid, token = self._login_token.rsplit("/", 1)
        url = self._to_url("edge/library-entries")
        params = {
            "filter[user_id]": uid,
            "filter[anime_id]": kitsu_id
            }
        scrobble = self._send_request(url, headers=self.__header(token), params=params)
        item_dict = json.loads(scrobble)
        if len(item_dict['data']) == 0:
            return lambda: self.__post_params(url, episode, kitsu_id, token, uid)

        animeid = item_dict['data'][0]['id']
        return lambda: self.__patch_params(url, animeid, episode, token)

    def __post_params(self, url, episode, kitsu_id, token, uid):
        params = {
                "data": {
                    "type": "libraryEntries",
                    "attributes": {
                        'status': 'current',
                        'progress': int(episode)
                        },
                    "relationships":{
                        "user":{
                            "data":{
                                "id": int(uid),
                                "type": "users"
                            }
                       },
                      "anime":{
                            "data":{
                                "id": int(kitsu_id),
                                "type": "anime"
                            }
                        }
                    }
                }
            }

        self._post_request(url, headers=self.__header(token), json=params)

    def __patch_params(self, url, animeid, episode, token):
        params = {
            'data': {
                'id': int(animeid),
                'type': 'libraryEntries',
                'attributes': {
                    'progress': int(episode)
                    }
                }
            }

        self._patch_request("%s/%s" %(url, animeid), headers=self.__header(token), json=params)

    def __get_sort(self):
        sort_types = {
            "Date Updated": "-progressed_at",
            "Progress": "-progress",
            "Title": "anime.titles." + self.__get_title_lang(),
            }

        return sort_types[self._sort]

    def __get_title_lang(self):
        title_langs = {
            "Canonical": "canonical",
            "English": "en",
            "Romanized": "en_jp",
            }

        return title_langs[self._title_lang]
