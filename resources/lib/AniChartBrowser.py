import itertools
import requests
import json
import time
import datetime
from ui import utils

class AniChartBrowser():
    _URL = "https://graphql.anilist.co"

    def _handle_paging(self, hasNextPage, base_url, page):
        if not hasNextPage:
            return []

        next_page = page + 1
        name = "Next Page (%d)" %(next_page)
        return [utils.allocate_item(name, base_url % next_page, True, None)]
    
    def get_airing(self, page=1):
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
        result = requests.post(self._URL, json={'query': query, 'variables': variables})
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

    def _parse_view(self, base):
        return [
            utils.allocate_item("%s" % base["name"],
                                base["url"],
                                True,
                                base["image"],
                                base["plot"])
            ]
