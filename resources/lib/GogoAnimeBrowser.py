import json
import requests
from bs4 import BeautifulSoup
from ui import utils
from ui.BrowserBase import BrowserBase

class GogoAnimeBrowser(BrowserBase):
    _BASE_URL = "https://www3.gogoanime.io"

    _HEADERS = {
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 \Firefox/56.0"
        }

    def _parse_anime_view(self, res):
        url = (res.attrs['href']).rsplit('/', 1)[1]
        name = res.text
        image = res.find('div')['style'].split('"')[1]
        return utils.allocate_item(name, "gogo_animes/" + url, True, image)

    def _json_request(self, url, params):
        response = requests.get(url, headers=self._HEADERS, params=params)
        return response.json()

    def _get_request(self, url, params=None):
        response = requests.get(url, headers=self._HEADERS, params=params)
        return response.text

    def _process_anime_view(self, url, params):
        json_resp = self._json_request(url, params)
        soup = BeautifulSoup(json_resp['content'], 'html.parser')
        results = soup('a', class_='ss-title')

        all_results = map(self._parse_anime_view, results)

        return all_results

    def _get_anime_info(self, anime_url):
        anime_url = self._to_url("category/%s" % anime_url)
        episode_list_url = 'https://ajax.apimovie.xyz/ajax/load-list-episode'
        resp = self._get_request(anime_url)
        soup = BeautifulSoup(resp, 'html.parser')

        anime_id = soup.select_one('input#movie_id').attrs['value']
        params = {
            'default_ep': 0,
            'ep_start': 0,
            'ep_end': 999999,  # Using a very big number works :)
            'id': anime_id,
            }

        res = self._get_request(episode_list_url, params=params)
        soup = BeautifulSoup(res, 'html.parser')

        epurls = list(
            [(a.get('href').strip(), a.select('div[class="name"]')[0].text)
             for a in soup.select('li a')]
            )

        return epurls

    def _parse_ep_view(self, res):
        url = res[0]
        name = res[1]
        image = ''
        return utils.allocate_item(name, "gogo_play/" + url, False, image)

    def get_anime_episodes(self, anime_url, desc_order):
        episodes = self._get_anime_info(anime_url)
        results = map(self._parse_ep_view, episodes)
        if not desc_order:
            results = reversed(results)

        return results

    def search_site(self, search_string, page=1):
        url = 'https://ajax.apimovie.xyz/site/loadAjaxSearch'
        params = {
            'keyword': search_string,
            'id': -1,
            'link_web': self._BASE_URL
            }

        return self._process_anime_view(url, params)

    def get_episode_sources(self, anime_url):
        anime_url = self._to_url(anime_url)
        resp = self._get_request(anime_url)
        soup = BeautifulSoup(resp, 'html.parser')
        sources = {}

        for element in soup.select('.anime_muti_link > ul > li'):
            server = element.get('class')[0]
            link = element.a.get('data-video')

            if server == 'mp4':
                server = 'mp4upload'
            elif server != 'xstreamcdn':
                continue
            sources.update({server: link})

        return sources
