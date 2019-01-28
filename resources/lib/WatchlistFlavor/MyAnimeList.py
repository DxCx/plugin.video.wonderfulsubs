import re
import bs4 as bs
import itertools
import json
import requests
from WatchlistFlavorBase import WatchlistFlavorBase

class MyAnimeListWLF(WatchlistFlavorBase):
    _TITLE = "MyAnimeList"
    _NAME = "mal"
    _IMAGE = "https://myanimelist.cdn-dena.com/images/mal-logo-xsmall@2x.png?v=160803001"

    def login(self):
        s = requests.session()

        crsf_res = s.get('https://myanimelist.net/').text
        crsf = (re.compile("<meta name='csrf_token' content='(.+?)'>").findall(crsf_res))[0]

        payload = {
            "user_name": self._username,
            "password": self._password,
            "cookie": 1,
            "sublogin": "Login",
            "submit": 1,
            "csrf_token": crsf
            }

        url = "https://myanimelist.net/login.php?from=%2F"
        s.get(url)
        result = s.post(url, data=payload)
        soup = bs.BeautifulSoup(result.text, 'html.parser')
        results = soup.find_all('div', attrs={"class":"badresult"})

        if results:
            return

        return self._format_login_data(self._username, '', ('%s/%s' % (s.cookies['MALHLOGSESSID'], s.cookies['MALSESSIONID'])))

    def watchlist(self):
        url = "https://myanimelist.net/animelist/%s" % (self._login_name)
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
        result = requests.get(url)
        soup = bs.BeautifulSoup(result.text)
        results = [x for x in soup.find_all('a', {'class': 'status-button'})]
        all_results = map(self._base_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def get_watchlist_status(self, status):
        params = {
            "status": status
            }

        url = "https://myanimelist.net/animelist/%s" % (self._login_name)
        return self._process_status_view(url, params, "watchlist/%d", page=1)

    def _process_status_view(self, url, params, base_plugin_url, page):
        result = requests.get(url, params=params).text
        soup = bs.BeautifulSoup(result)
        table = soup.find('table', attrs={'class':'list-table'})
        table_body = table.attrs['data-items']
        results = json.loads(table_body)
        all_results = map(self._base_watchlist_status_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_status_view(self, res):
        base = {
            "name": '%s - %d/%d' % (res["anime_title"], res["num_watched_episodes"], res["anime_num_episodes"]),
            "url": "watchlist_query/%s/%s" % (res["anime_title"], res["anime_id"]),
            "image": res["anime_image_path"],
            "plot": '',
        }

        return self._parse_view(base)

