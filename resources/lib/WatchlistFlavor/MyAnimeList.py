import re
import bs4 as bs
import itertools
import json
import requests
from WatchlistFlavorBase import WatchlistFlavorBase

class MyAnimeListWLF(WatchlistFlavorBase):
    _URL = "https://myanimelist.net"
    _TITLE = "MyAnimeList"
    _NAME = "mal"
    _IMAGE = "https://myanimelist.cdn-dena.com/images/mal-logo-xsmall@2x.png?v=160803001"

    def login(self):
        s = requests.session()

        crsf_res = s.get(self._URL).text
        crsf = (re.compile("<meta name='csrf_token' content='(.+?)'>").findall(crsf_res))[0]

        payload = {
            "user_name": self._username,
            "password": self._password,
            "cookie": 1,
            "sublogin": "Login",
            "submit": 1,
            "csrf_token": crsf
            }

        url = self._to_url("login.php?from=%2F")
        s.get(url)
        result = s.post(url, data=payload)
        soup = bs.BeautifulSoup(result.text, 'html.parser')
        results = soup.find_all('div', attrs={"class":"badresult"})

        if results:
            return

        return self._format_login_data(self._username, '', ('%s/%s' % (s.cookies['MALHLOGSESSID'], s.cookies['MALSESSIONID'])))

    def watchlist(self):
        url = self._to_url("animelist/%s" % (self._login_name))
        return self._process_watchlist_view(url, '', "watchlist/%d", page=1)

    def _base_watchlist_view(self, res):
        base = {
            "name": res.text,
            "url": 'watchlist_status_type/' + (res['href']).rsplit('=', 1)[-1],
            "image": '',
            "plot": '',
        }

        return self._parse_view(base)

    def _process_watchlist_view(self, url, params, base_plugin_url, page):
        result = self._send_request(url)
        soup = bs.BeautifulSoup(result, 'html.parser')
        results = [x for x in soup.find_all('a', {'class': 'status-button'})]
        all_results = map(self._base_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def get_watchlist_status(self, status):
        params = {
            "status": status,
            "order": self.__get_sort(),
            }

        url = self._to_url("animelist/%s" % (self._login_name))
        return self._process_status_view(url, params, "watchlist/%d", page=1)

    def _process_status_view(self, url, params, base_plugin_url, page):
        result = self._send_request(url, params=params)
        soup = bs.BeautifulSoup(result, 'html.parser')
        table = soup.find('table', attrs={'class':'list-table'})
        table_body = table.attrs['data-items']
        results = json.loads(table_body)
        all_results = map(self._base_watchlist_status_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_status_view(self, res):
        IMAGE_ID_RE = re.search('anime/(.*).jpg', res["anime_image_path"])
        image_id = IMAGE_ID_RE.group(1)

        base = {
            "name": '%s - %d/%d' % (res["anime_title"], res["num_watched_episodes"], res["anime_num_episodes"]),
            "url": "watchlist_query/%s/%s" % (res["anime_title"], res["anime_id"]),
            "image": "https://myanimelist.cdn-dena.com/images/anime/%sl.jpg" %(image_id),
            "plot": '',
        }

        return self._parse_view(base)

    def __cookies(self):
        logsess_id, sess_id = self._login_token.rsplit("/", 1)

        cookies = {
            'MALHLOGSESSID': logsess_id,
            'MALSESSIONID': sess_id,
            'is_logged_in': '1'
            }

        return cookies

    def _kitsu_to_mal_id(self, kitsu_id):
        arm_resp = requests.get("https://arm.now.sh/api/v1/search?type=kitsu&id=" + kitsu_id)
        if arm_resp.status_code != 200:
            raise Exception("AnimeID not found")

        mal_id = json.loads(arm_resp.text)["services"]["mal"]
        return mal_id

    def watchlist_update(self, episode, kitsu_id):
        mal_id = self._kitsu_to_mal_id(kitsu_id)
        result = self._send_request(self._to_url("anime/%s" % (mal_id)), cookies=self.__cookies())
        soup = bs.BeautifulSoup(result, 'html.parser')
        csrf = soup.find("meta",  {"name":"csrf_token"})["content"]
        match = soup.find('h2', {'class' : 'mt8'})
        if match:
            url = self._to_url("ownlist/anime/edit.json")
        else:
            url = self._to_url("ownlist/anime/add.json")

        return self.__update_library(url, episode, mal_id, csrf)

    def __update_library(self, url, episode, mal_id, csrf):
        payload = {
            "anime_id": int(mal_id),
            "status": 1,
            "score": 0,
            "num_watched_episodes": int(episode),
            "csrf_token": csrf
            }

        self._post_request(url, headers={'Content-Type': 'application/json'}, cookies=self.__cookies(), json=payload)

    def __get_sort(self):
        sort_types = {
            "Anime Title": 1,
            "Last Updated": 5,
            "Progress": 12,
            }

        return sort_types[self._sort]
