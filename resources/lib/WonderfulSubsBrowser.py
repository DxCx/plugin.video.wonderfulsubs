import urllib
import math
import itertools
import json
import re
import requests
import bs4 as bs
from ui import utils, control
from ui.BrowserBase import BrowserBase

class WonderfulSubsBrowser(BrowserBase):
    _BASE_URL = "https://www.wonderfulsubs.com"
    _RESULTS_PER_SEARCH_PAGE = 25

    def _parse_anime_view(self, res):
        result = []
        image = res["poster_tall"]
        if image:
            image = image.pop()['source']
        else:
            image = None

        base = {
            "name": res["title"],
            "url": "animes/" + res["url"].replace("/watch/", ""),
            "image": image,
            "plot": res["description"],
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

    def _parse_history_view(self, res):
        name = res
        return utils.allocate_item(name, "search/" + name + "/1", True)

    def _parse_watchlist_anime_view(self, res):
        name = res[1]
        image = res[2]
        url = res[0]
        return utils.allocate_item(name, "animes/" + url, True, image)

    def _handle_paging(self, total_results, base_url, page):
        total_pages = int(math.ceil(total_results /
                                    float(self._RESULTS_PER_SEARCH_PAGE)))
        if page == total_pages:
            return []

        next_page = page + 1
        name = "Next Page (%d/%d)" % (next_page, total_pages)
        return [utils.allocate_item(name, base_url % next_page, True, None)]

    def _handle_watchlist_paging(self, results, base_url, page):
        pages_html = self._PAGES_WATCHLIST_TOTAL_RE.findall(str(results))
        # No Pages? empty list ;)
        if not len(pages_html):
            return []

        total_pages = int(self._PAGES_WATCHLIST_TOTAL_RE.findall(str(results))[-2])
        if page >= total_pages:
            return [] # Last page

        next_page = page + 1
        name = "Next Page (%d/%d)" % (next_page, total_pages)
        return [utils.allocate_item(name, base_url % next_page, True, None)]

    def _json_request(self, url, data):
        response = json.loads(self._get_request(url, data))
        if response["status"] != 200:
            raise Exception("Request %s returned with error code %d" % (url,
                                                                        response["status"]))

        return response["json"]


    def _process_anime_view(self, url, data, base_plugin_url, page):
        json_resp = self._json_request(url, data)
        results = json_resp["series"]
        total_results = json_resp["total_results"]

        all_results = map(self._parse_anime_view, results)
        all_results = list(itertools.chain(*all_results))

        all_results += self._handle_paging(total_results, base_plugin_url, page)
        return all_results

    def _format_episode(self, sname, anime_url, is_dubbed, ses_idx, einfo):
        desc = None if not einfo.has_key("description") else einfo["description"]
        image = None
        if einfo.has_key("thumbnail") and len(einfo["thumbnail"]):
            image = einfo["thumbnail"].pop().get("source", None)

        sources = self._format_sources(sname, is_dubbed, einfo)

        base = {}

        if einfo.has_key("ova_number"):
            base.update({
                "name": einfo["title"],
                "id": str(einfo["ova_number"]),
                "url": "play/%s/%s/%d/%s" % (anime_url,
                                          "dub" if is_dubbed else "sub",
                                          ses_idx,
                                          str(einfo["ova_number"])),
                "sources": sources,
                "image": image,
                "plot": desc,
            })

        else:
            base.update({
                "name": einfo["title"] if "Episode" in einfo["title"] else "Ep. %s (%s)" %(einfo["episode_number"], einfo["title"]), 
                "id": str(einfo["episode_number"]),
                "url": "play/%s/%s/%d/%s" % (anime_url,
                                          "dub" if is_dubbed else "sub",
                                          ses_idx,
                                          str(einfo["episode_number"])),
                "sources": sources,
                "image": image,
                "plot": desc,
            })
        return base

    def _format_sources(self, sname, is_dubbed, einfo): 
        sources = {}

        value = einfo.get("sources", None)
        if value is None:
            rlink = einfo["retrieve_url"]
            sources.update(self._format_link(sname, rlink))
            return sources

        source_obj = einfo["sources"]
        filter_sources = filter(lambda x: x["language"] == "dubs" if is_dubbed else x["language"] == "subs" , source_obj)

        for sindex, i in enumerate(filter_sources):
            sname = "Server %d" %(sindex)
            rlink = i["retrieve_url"]
            sources.update(self._format_link(sname, rlink))

        return sources

    def _format_link(self, sname, rlink):
        if type(rlink) is list:
            rlink = rlink.pop()

        video_data = {
            "code": rlink,
            }
        link = "%s?%s" % (self._to_url("api/media/stream"), urllib.urlencode(video_data))
        return {sname: link}

    def _get_anime_info_obj(self, anime_url):
        results = self._json_request(self._to_url("/api/media/series"), {
            "series": anime_url,
        })

        return results

    def _strip_seasons(self, server, is_dubbed):
        seasons = []
        seasons += server["media"]
        return seasons

    def _get_anime_info(self, anime_url, is_dubbed):
        obj = self._get_anime_info_obj(anime_url)
        image = obj["poster_tall"]
        if image:
            image = image.pop()['source']
        else:
            image = None

        seasons = {}
        ses_idx = 0
        for sindex, s in enumerate(obj["seasons"].values()):
            for season_col in self._strip_seasons(s, is_dubbed):
                ses_obj = {
                    "episodes": {},
                    "id": ses_idx,
                    "url": "animes/%s/%s/%d" % (
                        anime_url,
                        "dub" if is_dubbed else "sub",
                        ses_idx,
                    ),
                }

                if not season_col.has_key("title"):
                    if season_col["type"] == "specials":
                        ses_obj["name"] = "Special"
                    else:
                        ses_obj["name"] = "Episodes"
                else:
                    ses_obj["name"] = season_col["title"]

                # TODO: by ID, not name
                if seasons.has_key(ses_obj["name"]):
                    ses_obj = seasons[ses_obj["name"]]
                else:
                    seasons[ses_obj["name"]] = ses_obj
                    ses_idx += 1
                eps = ses_obj["episodes"]

                for einfo in season_col["episodes"]:
                    ep_flv_dubbed = einfo.get("is_dubbed", None)
                    if not ep_flv_dubbed and is_dubbed:
                        continue

                    ep_info = self._format_episode("Server %d" % sindex,
                                                   anime_url, is_dubbed,
                                                   ses_obj["id"], einfo)
                    if not eps.has_key(ep_info["id"]):
                        eps[ep_info["id"]] = ep_info
                        continue

                    old_ep_info = eps[ep_info["id"]]
                    if not old_ep_info["image"]:
                        old_ep_info["image"] = ep_info["image"]
                    if not old_ep_info["plot"]:
                        old_ep_info["name"] = ep_info["name"]
                        old_ep_info["plot"] = ep_info["plot"]
                    old_ep_info["sources"].update(ep_info["sources"])

        return {
            "name": obj["title"],
            "image": image,
            "plot": obj["description"],
            "url": "animes/%s/%s" % (anime_url, "dub" if is_dubbed else "sub"),
            "seasons": dict([(str(i['id']), i) for i in seasons.values()]),
        }

    def _get_anime_episodes(self, info, season):
        season = info["seasons"][season]
        episodes = sorted(season["episodes"].values(), reverse=True, key=lambda x:
                          float(x["id"]))
        return map(lambda x: utils.allocate_item(x['name'],
                                                 x['url'],
                                                 False,
                                                 x['image'],
                                                 x['plot']), episodes)

    def search_site(self, search_string, page=1):
        data = {
            "q": search_string,
            "count": self._RESULTS_PER_SEARCH_PAGE,
            "index": (page-1) * self._RESULTS_PER_SEARCH_PAGE,
        }

        url = self._to_url("api/media/search")
        return self._process_anime_view(url, data, "search/%s/%%d" % search_string, page)

    # TODO: Not sure i want this here..
    def search_history(self,search_array):
    	result = map(self._parse_history_view,search_array)
    	result.insert(0,utils.allocate_item("New Search", "search", True))
    	result.insert(len(result),utils.allocate_item("Clear..", "clear_history", True))
    	return result

    def get_by_letter(self, letter, page = 1):
        data = {
            "letter": letter.lower(),
            "count": self._RESULTS_PER_SEARCH_PAGE,
            "index": (page-1) * self._RESULTS_PER_SEARCH_PAGE,
        }
        url = self._to_url("api/media/all")
        return self._process_anime_view(url, data, "letter/%s/%%d" % letter, page)

    def get_all(self,  page=1):
        data = {
            "count": self._RESULTS_PER_SEARCH_PAGE,
            "index": (page-1) * self._RESULTS_PER_SEARCH_PAGE,
        }
        url = self._to_url("api/media/all")
        return self._process_anime_view(url, data, "all/%d", page)

    def get_popular(self,  page=1):
        data = {
            "count": self._RESULTS_PER_SEARCH_PAGE,
            "index": (page-1) * self._RESULTS_PER_SEARCH_PAGE,
        }
        url = self._to_url("api/media/popular")
        return self._process_anime_view(url, data, "popular/%d", page)

    def get_latest(self, page=1):
        data = {
            "count": self._RESULTS_PER_SEARCH_PAGE,
            "index": (page-1) * self._RESULTS_PER_SEARCH_PAGE,
        }
        url = self._to_url("api/media/latest")
        return self._process_anime_view(url, data, "latest/%d", page)

    def get_anime_metadata(self, anime_url, is_dubbed):
        info = self._get_anime_info(anime_url, is_dubbed)
        return (info["name"], info["image"])

    def get_anime_seasons(self, anime_url, is_dubbed):
        info = self._get_anime_info(anime_url, is_dubbed)
        if len(info["seasons"]) == 1:
            return self._get_anime_episodes(info, info["seasons"].keys().pop())

        seasons = sorted(info["seasons"].values(), key=lambda x: x["id"])
        return map(lambda x: utils.allocate_item(x['name'],
                                                 x['url'],
                                                 True,
                                                 info["image"],
                                                 info["plot"]), seasons)

    def get_anime_episodes(self, anime_url, is_dubbed, season):
        info = self._get_anime_info(anime_url, is_dubbed)
        return self._get_anime_episodes(info, season)

    def get_episode_sources(self, anime_url, is_dubbed, season, episode):
        info = self._get_anime_info(anime_url, is_dubbed)
        if not info["seasons"]: return []
        season = info["seasons"][season]

        ep = season["episodes"][episode]
        return ep["sources"]

class AuthTrack():
    def mal_login(self, flavor, flavor_key, name_key, image_key, token_key):
        s = requests.session()
        token_url = s.get('https://myanimelist.net/').text
        crsf = re.compile("<meta name='csrf_token' content='(.+?)'>").findall(token_url)
        token = crsf[0]
        payload = {
            "user_name": control.getSetting("MyAnimeList.username"),
            "password": control.getSetting("MyAnimeList.password"),
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
            return control.ok_dialog('Login', 'Incorrect username or password')
        control.setSetting(token_key, '%s/%s' %(s.cookies['MALHLOGSESSID'], s.cookies['MALSESSIONID']))
        control.setSetting(image_key, '')
        control.setSetting(name_key, control.getSetting("MyAnimeList.username"))
        control.setSetting(flavor_key, flavor)
        control.refresh()

    #Ask DxCx how to handle retrieving token
    def anilist_login(self, flavor, flavor_key, name_key, image_key, token_key):
        control.setSetting(flavor_key, flavor)
        control.refresh()

    def kitsu_login(self, flavor, flavor_key, name_key, image_key, token_key):
        r = requests.post('https://kitsu.io/api/oauth/token', params={"grant_type": "password", "username": '%s' %(control.getSetting("Kitsu.email")), "password": '%s' %(control.getSetting("Kitsu.password"))})
        if r.status_code != 200:
            return control.ok_dialog('Login', 'Incorrect username or password')
        data = json.loads(r.text)
        user_res = requests.get('https://kitsu.io/api/edge/users?filter[self]=true', headers=self.kitsu_headers(data['access_token']))
        data2 = json.loads(user_res.text)["data"][0]
        control.setSetting(token_key, '%s/%s' %(data2['id'], data['access_token']))
        control.setSetting(image_key, '')
        control.setSetting(name_key, data2["attributes"]["name"])
        control.setSetting(flavor_key, flavor)
        control.refresh()

    def kitsu_headers(self, token):
        headers = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': "Bearer {}".format(token),
            }
        return headers

    def wonderfulsubs_login(self, flavor, flavor_key, name_key, image_key, token_key):
        r = requests.post('https://www.wonderfulsubs.com/api/users/login', json={"username":control.getSetting('WonderfulSubs.username'),"password":control.getSetting('WonderfulSubs.password')})
        data = json.loads(r.text)
        if data['success'] is not True:
            return control.ok_dialog('Login', 'Incorrect username or password')
        control.setSetting(token_key, '%s/%s' %(data['data']['_id'], data['token']))
        control.setSetting(image_key, data['data']['profile_pic'])
        control.setSetting(name_key, data['data']['username'])
        control.setSetting(flavor_key, flavor)
        control.refresh()

class WatchlistTrack(BrowserBase):
    def wonderfulsubs_watchlist(self, name_key, token_key):
        _id, token = control.getSetting(token_key).rsplit("/", 1)
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

    def kitsu_watchlist(self, name_key, token_key):
        _id, token = control.getSetting(token_key).rsplit("/", 1)
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
            "url": 'kitsu/'+res,
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

        _id, token = control.getSetting(token_key).rsplit("/", 1)
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

    def mal_watchlist(self, name_key, token_key):
        url = "https://myanimelist.net/animelist/%s" %(control.getSetting(name_key))
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
            "url": 'mal/' + (res['href']).rsplit('=', 1)[-1],
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

    def get_mal_watchlist_status(self, name_key, token_key, status):
        params = {
            "status": status
            }
        
        url = "https://myanimelist.net/animelist/%s" %(control.getSetting(name_key))
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
            "image": 'https://myanimelist.cdn-dena.com/'+ res["anime_image_path"][42:],
            "plot": '',
        }

        result.append(utils.allocate_item("%s" % base["name"],
                                          base["url"],
                                          True,
                                          base["image"],
                                          base["plot"]))

        return result
