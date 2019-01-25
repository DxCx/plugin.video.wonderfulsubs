import itertools
import json
import re
import requests
import bs4 as bs
from ui import utils

class AuthToken():
    def mal_login(self, name, password):
        s = requests.session()
        token_url = s.get('https://myanimelist.net/').text
        crsf = re.compile("<meta name='csrf_token' content='(.+?)'>").findall(token_url)
        token = crsf[0]

        payload = {
            "user_name": name,
            "password": password,
            "cookie": 1,
            "sublogin": "Login",
            "submit": 1,
            "csrf_token": token
            }

        url = "https://myanimelist.net/login.php?from=%2F"
        s.get(url)
        result = s.post(url, data=payload)
        soup = bs.BeautifulSoup(result.text, 'html.parser')
        results = soup.find_all('div', attrs={"class":"badresult"})

        if results:
            return []

        return [('%s/%s' %(s.cookies['MALHLOGSESSID'], s.cookies['MALSESSIONID'])), '']

    #Ask DxCx how to handle retrieving token
    def anilist_login(self):
        return []

    def kitsu_login(self, name, password):
        r = requests.post('https://kitsu.io/api/oauth/token', params={"grant_type": "password", "username": '%s' %(name), "password": '%s' %(password)})

        if r.status_code != 200:
            []

        data = json.loads(r.text)
        user_res = requests.get('https://kitsu.io/api/edge/users?filter[self]=true', headers=self.kitsu_headers(data['access_token']))
        data2 = json.loads(user_res.text)["data"][0]

        return [('%s/%s' %(data2['id'], data['access_token'])), '',  (data2["attributes"]["name"])]

    def kitsu_headers(self, token):
        headers = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': "Bearer {}".format(token),
            }

        return headers

    def wonderfulsubs_login(self, name, password):
        r = requests.post('https://www.wonderfulsubs.com/api/users/login', json={"username":name,"password":password})
        data = json.loads(r.text)

        if data['success'] is not True:
            return []

        return [('%s/%s' %(data['data']['_id'], data['token'])), (data['data']['profile_pic']), (data['data']['username'])]

class WatchList():
    def wonderfulsubs_watchlist(self, token_key, name_key):
        _id, token = token_key.rsplit("/", 1)
        headers = self.wonderfulsubs_headers(token)
        url = 'https://www.wonderfulsubs.com/api/watchlist/list?_id=%s' %(_id)
        return self._process_wonderfulsubs_watchlist_view(url, headers, "wonderfulsubs/%d", page=1)

    def wonderfulsubs_headers(self, token):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(token)
            }

        return headers

    def _parse_wonderfulsubs_watchlist_view(self, res):
        result = []
        
        base = {
            "name": '%s' %(res['title']),
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

    def _parse_watchlist_anime_view(self, res):
        name = res[1]
        image = res[2]
        url = res[0]
        return utils.allocate_item(name, "animes/" + url, True, image)

    def _process_wonderfulsubs_watchlist_view(self, url, headers, base_plugin_url, page):
        r = requests.get(url, headers=headers)
        results = json.loads(r.text)['data']['watch_list']
        all_results = map(self._parse_wonderfulsubs_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def kitsu_watchlist(self, token_key, name_key):
        _id, token = token_key.rsplit("/", 1)
        headers = self.kitsu_headers(token)
        params = {"filter[user_id]": _id}
        url = "https://kitsu.io/api/edge/library-entries"
        return self._process_kitsu_watchlist_view(url, params, headers, "kitsu/%d", page=1)

    def kitsu_headers(self, token):
        headers = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': "Bearer {}".format(token),
            }
        return headers

    def _parse_kitsu_watchlist_view(self, res):
        result = []
        
        base = {
            "name": res.capitalize(),
            "url": 'watchlist_flavor/kitsu/'+res,
            "image": '',
            "plot": '',
        }

        result.append(utils.allocate_item("%s" % base["name"],
                                          base["url"],
                                          True,
                                          base["image"],
                                          base["plot"]))

        return result

    def _process_kitsu_watchlist_view(self, url, params, headers, base_plugin_url, page):
        result = requests.get(url, params=params, headers=headers).text
        results = json.loads(result)["meta"]["statusCounts"]
        all_results = map(self._parse_kitsu_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def get_kitsu_watchlist_status(self, token_key, status):
        if status == "onHold":
            status = "on_hold"

        _id, token = token_key.rsplit("/", 1)
        headers = self.kitsu_headers(token)
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
            "sort": "anime.titles.canonical"
            }

        return self._process_kitsu_watchlist_status_view(url, params, headers, "kitsu/%d", page=1)

    def _process_kitsu_watchlist_status_view(self, url, params, headers, base_plugin_url, page):
        result = requests.get(url, params=params, headers=headers).text
        results = json.loads(result)["included"][1:]
        results2 = json.loads(result)["data"]
        all_results = map(self._parse_kitsu_watchlist_status_view, results, results2)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _parse_kitsu_watchlist_status_view(self, res, res2):
        result = []

        base = {
            "name": '%s - %d/%d' %(res["attributes"]['canonicalTitle'], res2["attributes"]['progress'], res["attributes"]['episodeCount'] if res["attributes"]['episodeCount'] is not None else 0),
            "url": "watchlist_query/%s/%s" % (res["attributes"]['canonicalTitle'], res["id"]),
            "image": res["attributes"]['posterImage']['medium'],
            "plot": res["attributes"]["synopsis"],
        }

        result.append(utils.allocate_item("%s" % base["name"],
                                          base["url"],
                                          True,
                                          base["image"],
                                          base["plot"]))

        return result

    def mal_watchlist(self, token_key, name_key=""):
        url = "https://myanimelist.net/animelist/%s" %(name_key)
        return self._process_mal_watchlist_view(url, '', "mal/%d", page=1)

    def mal_cookies(self, logsess_id, sess_id):
        cookies = {
            'MALHLOGSESSID': logsess_id,
            'MALSESSIONID': sess_id,
            'is_logged_in': '1'
            }
        return cookies

    def _parse_mal_watchlist_view(self, res):
        result = []
        
        base = {
            "name": res.text,
            "url": 'watchlist_flavor/mal/' + (res['href']).rsplit('=', 1)[-1],
            "image": '',
            "plot": '',
        }

        result.append(utils.allocate_item("%s" % base["name"],
                                          base["url"],
                                          True,
                                          base["image"],
                                          base["plot"]))

        return result

    def _process_mal_watchlist_view(self, url, params, base_plugin_url, page):
        result = requests.get(url)
        soup = bs.BeautifulSoup(result.text)
        results = [x for x in soup.find_all('a', {'class': 'status-button'})]
        all_results = map(self._parse_mal_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def get_mal_watchlist_status(self, name_key, status):
        params = {
            "status": status
            }
        
        url = "https://myanimelist.net/animelist/%s" %(name_key)
        return self._process_mal_watchlist_status_view(url, params, "mal/%d", page=1)

    def _process_mal_watchlist_status_view(self, url, params, base_plugin_url, page):
        result = requests.get(url, params=params).text
        soup = bs.BeautifulSoup(result)
        table = soup.find('table', attrs={'class':'list-table'})
        table_body = table.attrs['data-items']
        results = json.loads(table_body)
        all_results = map(self._parse_mal_watchlist_status_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _parse_mal_watchlist_status_view(self, res):
        result = []

        base = {
            "name": '%s - %d/%d' %(res["anime_title"], res["num_watched_episodes"], res["anime_num_episodes"]),
            "url": "watchlist_query/%s/%s" %(res["anime_title"], res["anime_id"]),
            "image": res["anime_image_path"],
            "plot": '',
        }

        result.append(utils.allocate_item("%s" % base["name"],
                                          base["url"],
                                          True,
                                          base["image"],
                                          base["plot"]))

        return result
