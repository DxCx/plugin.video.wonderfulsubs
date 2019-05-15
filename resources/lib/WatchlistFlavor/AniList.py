import itertools
import json
from WatchlistFlavorBase import WatchlistFlavorBase

class AniListWLF(WatchlistFlavorBase):
    _URL = "https://graphql.anilist.co"
    _TITLE = "AniList"
    _NAME = "anilist"
    _IMAGE = "https://anilist.co/img/icons/logo_full.png"

    #Not login, but retrieveing userId for watchlist
    def login(self):
        query = '''
        query ($name: String) {
            User(name: $name) {
                id
                }
            }
        '''

        variables = {
            "name": self._username
            }

        result = self._post_request(self._URL, json={'query': query, 'variables': variables})
        results = result.json()

        if results.has_key("errors"):
            return

        userId = results['data']['User']['id']

        return self._format_login_data(self._username,
                                       '',
                                       str(userId))

    def watchlist(self):
        return self._process_watchlist_view("watchlist/%d", page=1)

    def _base_watchlist_view(self, res):
        base = {
            "name": res[0],
            "url": 'watchlist_status_type/' + str(res[1]),
            "image": '',
            "plot": '',
        }

        return self._parse_view(base)

    def _process_watchlist_view(self, base_plugin_url, page):
        all_results = map(self._base_watchlist_view, self.__anilist_statuses())
        all_results = list(itertools.chain(*all_results))
        return all_results

    def __anilist_statuses(self):
        statuses = [
            ("Current", "CURRENT"),
            ("Rewatching", "REPEATING"),
            ("Plan to Watch", "PLANNING"),
            ("Paused", "PAUSED"),
            ("Completed", "COMPLETED"),
            ("Dropped", "DROPPED"),
            ]

        return statuses

    def get_watchlist_status(self, status):
        query = '''
        query ($userId: Int, $userName: String, $status: MediaListStatus, $type: MediaType, $sort: [MediaListSort]) {
            MediaListCollection(userId: $userId, userName: $userName, status: $status, type: $type, sort: $sort) {
                lists {
                    entries {
                        ...mediaListEntry
                        }
                    }
                }
            }

        fragment mediaListEntry on MediaList {
            id
            mediaId
            status
            progress
            customLists
            media {
                id
                title {
                    userPreferred
                }
                coverImage {
                    extraLarge
                }
                status
                episodes

            }
        }
        '''

        variables = {
            'userId': int(self._login_token),
            'username': self._username,
            'status': status,
            'type': 'ANIME',
            'sort': [self.__get_sort()]
            }

        return self._process_status_view(query, variables, "watchlist/%d", page=1)

    def _process_status_view(self, query, variables, base_plugin_url, page):
        result = self._post_request(self._URL, json={'query': query, 'variables': variables})
        results = result.json()

        if results.has_key("errors"):
            return

        entries = results['data']['MediaListCollection']['lists'][0]['entries']
        all_results = map(self._base_watchlist_status_view, reversed(entries))
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_status_view(self, res):
        base = {
            "name": '%s - %d/%d' % (res['media']["title"]["userPreferred"], res['progress'], res['media']['episodes'] if res['media']['episodes'] is not None else 0),
            "url": "watchlist_query/%s" % (res['media']["title"]["userPreferred"]),
            "image": res['media']['coverImage']['extraLarge'],
            "plot": '',
        }

        return self._parse_view(base)

    def __get_sort(self):
        sort_types = {
            "Score": "SCORE",
            "Progress": "PROGRESS",
            "Last Updated": "UPDATED_TIME",
            "Last Added": "ADDED_TIME",
            }

        return sort_types[self._sort]

    def __headers(self):
        token = self._password
        headers = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            }

        return headers

    def _kitsu_to_anilist_id(self, kitsu_id):
        arm_resp = self._get_request("https://arm.now.sh/api/v1/search?type=kitsu&id=" + kitsu_id)
        if arm_resp.status_code != 200:
            raise Exception("AnimeID not found")

        anilist_id = arm_resp.json()["services"]["anilist"]
        return anilist_id

    def watchlist_update(self, episode, kitsu_id):
        anilist_id = self._kitsu_to_anilist_id(kitsu_id)
        return lambda: self.__update_library(episode, anilist_id)

    def __update_library(self, episode, anilist_id):
        query = '''
        mutation ($mediaId: Int, $progress : Int, $status: MediaListStatus) {
            SaveMediaListEntry (mediaId: $mediaId, progress: $progress, status: $status) {
                id
                progress
                status
                }
            }
        '''

        variables = {
            'mediaId': int(anilist_id),
            'progress': int(episode),
            'status': 'CURRENT'
            }

        self._post_request(self._URL, headers=self.__headers(), json={'query': query, 'variables': variables})
