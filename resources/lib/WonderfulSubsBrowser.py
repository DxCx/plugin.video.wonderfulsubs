import urllib
import itertools
import json
from ui import utils
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

    def _handle_paging(self, results, base_url, page):
        pages_html = self._PAGES_RE.findall(results)
        # No Pages? empty list ;)
        if not len(pages_html):
            return []

        total_pages = int(self._PAGES_TOTAL_RE.findall(pages_html[0])[0])
        if page >= total_pages:
            return [] # Last page

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
        # TODO: remove/alter this
        if not url.endswith("search") and not url.endswith("anime"):
            data = {}


        response = json.loads(self._get_request(url, data))
        if response["status"] != 200:
            raise Exception("Request %s returned with error code %d" % (url,
                                                                        response["status"]))

        return response["json"]


    def _process_anime_view(self, url, data, base_plugin_url, page):
        results = self._json_request(url, data)["series"]

        all_results = map(self._parse_anime_view, results)
        all_results = list(itertools.chain(*all_results))

        # TODO: Paging
        # all_results += self._handle_paging(results, base_plugin_url, page)
        return all_results

    def _format_episode(self, sname, anime_url, is_dubbed, ses_idx, einfo):
        desc = None if not einfo.has_key("description") else einfo["description"]
        image = None
        if einfo.has_key("thumbnail") and len(einfo["thumbnail"]):
            image = einfo["thumbnail"].pop().get("source", None)

        rlink = einfo["retreive_link"]
        if type(rlink) is list:
            rlink = rlink.pop()

        video_data = {
            "code": rlink,
        }
        link = "%s?%s" % (self._to_url("api/video"), urllib.urlencode(video_data))

        base = {}
        base.update({
            "name": einfo["title"],
            "id": str(einfo["episode_number"]),
            "url": "play/%s/%s/%d/%s" % (anime_url,
                                      "dub" if is_dubbed else "sub",
                                      ses_idx,
                                      str(einfo["episode_number"])),
            "sources": {sname: link},
            "image": image,
            "plot": desc,
        })
        return base

    def _get_anime_info_obj(self, anime_url):
        results = self._json_request(self._to_url("/api/anime"), {
            "series": anime_url,
        })

        return results

    def _strip_seasons(self, server, is_dubbed):
        seasons = []
        if is_dubbed:
            seasons += server["dubs"]
        else:
            seasons += server["subs"]
            seasons += server["main"]
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
                    if None == einfo["episode_number"]:
                        print "[+] Skip %s" % einfo
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
            "index": (page-1) * self._RESULTS_PER_SEARCH_PAGE,
        }

        url = self._to_url("api/search")
        return self._process_anime_view(url, data, "search/%s/%%d" % search_string, page)

    # TODO: Not sure i want this here..
    def search_history(self,search_array):
    	result = map(self._parse_history_view,search_array)
    	result.insert(0,utils.allocate_item("New Search", "search", True))
    	result.insert(len(result),utils.allocate_item("Clear..", "clear_history", True))
    	return result

    def get_all(self,  page=1):
        data = {
            "page": page,
        }
        url = self._to_url("api/all")
        return self._process_anime_view(url, data, "all/%d", page)

    def get_popular(self,  page=1):
        data = {
            "page": page,
        }
        url = self._to_url("api/popular")
        return self._process_anime_view(url, data, "popular/%d", page)

    def get_latest(self, page=1):
        data = {
            "page": page,
        }
        url = self._to_url("api/latest")
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
