import itertools
import json
import time
import datetime
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
            "Last Updated": "UPDATE_TIME",
            "Last Added": "ADDED_TIME",
            }

        return sort_types[self._sort]

    def watchlist_update(self, episode, kitsu_id):
        return False

class AniChart(WatchlistFlavorBase):
    _URL = "https://graphql.anilist.co"

    def __init__(self):
        pass

    def _handle_paging(self, hasNextPage, base_url, page):
        if not hasNextPage:
            return []

        next_page = page + 1
        name = "Next Page (%d)" %(next_page)
        return self._allocate_page(name, base_url % next_page)
    
    def get_airing(self, page):
        today = datetime.date.today()
        today_ts = int(time.mktime(today.timetuple()))
        weekStart = today_ts - 86400
        weekEnd = today_ts + (86400*6)

        query = '''
        query (
                $weekStart: Int,
                $weekEnd: Int,
                $page: Int,
        ){
                Page(page: $page) {
                        pageInfo {
                                hasNextPage
                                total
                        }
                        airingSchedules(
                                airingAt_greater: $weekStart
                                airingAt_lesser: $weekEnd
                        ) {
                                id
                                episode
                                airingAt
                                media {
                                        
        id
        idMal
        title {
                romaji
                native
                english
        }
        description
        isAdult
        coverImage {
                extraLarge
        }
                                }
                        }
                }
        }
        '''

        variables = {
            'weekStart': weekStart,
            'weekEnd': weekEnd,
            'page': page
            }

        return self._process_anichart_view(query, variables, "anichart_airing/%d", page)

    def _process_anichart_view(self, query, variables, base_plugin_url, page):
        result = self._post_request(self._URL, json={'query': query, 'variables': variables})
        results = result.json()

        if results.has_key("errors"):
            return

        json_res = results['data']['Page']
        filter_json = filter(lambda x: x['media']['isAdult'] == False, json_res['airingSchedules'])
        hasNextPage = json_res['pageInfo']['hasNextPage']

        all_results = map(self._base_anichart_view, filter_json)
        all_results = list(itertools.chain(*all_results))

        all_results += self._handle_paging(hasNextPage, base_plugin_url, page)
        return all_results

    def _base_anichart_view(self, res):
        airingAt = datetime.datetime.fromtimestamp(res['airingAt']).strftime('%I:%M %p on %a')
        ts = int(time.time())
        is_airing = 'airing' if res['airingAt'] > ts else "aired"

        base = {
            "name": "%s - [I]Ep %s %s at %s[/I]" % (res['media']['title']['romaji'],
                                                    res['episode'],
                                                    is_airing,
                                                    airingAt),
            "url": "watchlist_query/%s" % (res['media']['title']['romaji']),
            "image": res['media']['coverImage']['extraLarge'],
            "plot": res['media']['description'],
        }

        return self._parse_view(base)
