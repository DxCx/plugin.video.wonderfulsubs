import bs4 as bs, itertools, json, re, requests
from collections import defaultdict
from ui import control, utils
from ui.router import on_param, route, router_process
from WonderfulSubsBrowser import WonderfulSubsBrowser

LOGIN_KEY = "addon.login"
LOGIN_FLAVOR_KEY = "%s.flavor" % LOGIN_KEY
LOGIN_NAME_KEY = "%s.name" % LOGIN_KEY
LOGIN_IMAGE_KEY = "%s.image" % LOGIN_KEY
LOGIN_TOKEN_KEY = "%s.token" % LOGIN_KEY

class WatchlistFlavorBase(object):
    _TITLE = None
    _NAME = None
    _IMAGE = None

    def __init__(self, login_name, username, password, login_image, login_token):
        if isinstance(self, WatchlistFlavor):
            raise Exception("Base Class should not be created")

        self._login_name = login_name
        self._username = username
        self._password = password
        self._login_image = login_image
        self._login_token = login_token

    @classmethod
    def name(cls):
        if cls._NAME is None:
            raise Exception("Missing Name")

        return cls._NAME

    @property
    def image(self):
        if self._IMAGE is None:
            raise Exception("Missing Image")

        return self._IMAGE

    @property
    def title(self):
        if self._TITLE is None:
            raise Exception("Missing Title")

        return self._TITLE

    @property
    def login_name(self):
        return self._login_name

    def login(self):
        raise NotImplementedError("login should be implemented by subclass")

    def watchlist(self):
        raise NotImplementedError("watchlist should be implemented by subclass")

    def get_watchlist_status(self, status):
        raise NotImplementedError("get_watchlist_status should be implemented by subclass")

    def _format_login_data(self, name, image, token):
        login_data = {
            "name": name,
            "image": image,
            "token": token,
            }

        return login_data

    def _parse_view(self, base):
        return [
            utils.allocate_item("%s" % base["name"],
                                base["url"],
                                True,
                                base["image"],
                                base["plot"])
            ]

class WatchlistFlavor(object):
    _SELECTED = None

    @staticmethod
    def __get_flavor_class(name):
        for flav in WatchlistFlavorBase.__subclasses__():
            if flav.name() == name:
                return flav
        return None

    @staticmethod
    def __is_flavor_valid(name):
        return WatchlistFlavor.__get_flavor_class(name) != None

    @staticmethod
    def get_active_flavor():
        selected = control.getSetting(LOGIN_FLAVOR_KEY)
        if not selected:
            return None

        if not WatchlistFlavor._SELECTED:
            WatchlistFlavor._SELECTED = \
                    WatchlistFlavor.__get_flavor_class(selected)()

        return WatchlistFlavor._SELECTED

    @staticmethod
    def watchlist_request():
        return WatchlistFlavor.get_active_flavor().watchlist()

    @staticmethod
    def watchlist_status_request(status):
        return WatchlistFlavor.get_active_flavor().get_watchlist_status(status)

    @staticmethod
    def login_request(flavor):
        if not WatchlistFlavor.__is_flavor_valid(flavor):
            raise Exception("Invalid flavor %s" % flavor)

        flavor_class = WatchlistFlavor.__get_flavor_class(flavor)()
        return WatchlistFlavor.__set_login(flavor,
                                           flavor_class.login())

    @staticmethod
    def __set_login(flavor, res):
        if not res:
            return control.ok_dialog('Login', 'Incorrect username or password')

        control.setSetting(LOGIN_FLAVOR_KEY, flavor)
        control.setSetting(LOGIN_TOKEN_KEY, res['token'])
        control.setSetting(LOGIN_IMAGE_KEY, res['image'])
        control.setSetting(LOGIN_NAME_KEY, res['name'])
        control.refresh()

    @staticmethod
    def logout_request():
        control.setSetting(LOGIN_FLAVOR_KEY, '')
        control.setSetting(LOGIN_NAME_KEY, '')
        control.setSetting(LOGIN_IMAGE_KEY, '')
        control.setSetting(LOGIN_TOKEN_KEY, '')
        control.refresh()

    def __init__(self):
        raise Exception("Static Class should not be created")

# TODO: Move into thier own files, Base class should be its own file too,
# Each file imports from this base class.
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

    def cookies(self):
        logsess_id, sess_id = self._login_token.rsplit("/", 1)

        cookies = {
            'MALHLOGSESSID': logsess_id,
            'MALSESSIONID': sess_id,
            'is_logged_in': '1'
            }

        return cookies

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

class KitsuWLF(WatchlistFlavorBase):
    _TITLE = "Kitsu"
    _NAME = "kitsu"
    _IMAGE = "https://canny.io/images/13895523beb5ed9287424264980221d4.png"

    def login(self):
        r = requests.post('https://kitsu.io/api/oauth/token', params={
            "grant_type": "password",
            "username": self._username,
            "password": self._password
        })

        if r.status_code != 200:
            return

        data = json.loads(r.text)
        user_res = requests.get('https://kitsu.io/api/edge/users?filter[self]=true',
                                headers=self.header(data['access_token']))

        data2 = json.loads(user_res.text)["data"][0]

        return self._format_login_data((data2["attributes"]["name"]),
                                       '',
                                       ('%s/%s' % (data2['id'], data['access_token'])))

    def header(self, token):
        header = {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'Authorization': "Bearer {}".format(token),
            }

        return header

    def watchlist(self):
        _id, token = self._login_token.rsplit("/", 1)
        headers = self.header(token)
        params = {"filter[user_id]": _id}
        url = "https://kitsu.io/api/edge/library-entries"
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
        result = requests.get(url, params=params, headers=headers).text
        results = json.loads(result)["meta"]["statusCounts"]
        all_results = map(self._base_watchlist_status_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def get_watchlist_status(self, status):
        if status == "onHold":
            status = "on_hold"

        _id, token = self._login_token.rsplit("/", 1)
        headers = self.header(token)
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
            "sort": "anime.titles.canonical",
            }

        return self._process_watchlist_view(url, params, headers, "watchlist/%d", page=1)

    def _process_watchlist_view(self, url, params, headers, base_plugin_url, page):
        result = requests.get(url, params=params, headers=headers).text
        results = json.loads(result)["included"][1:]
        results2 = json.loads(result)["data"]
        all_results = map(self._base_watchlist_view, results, results2)
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _base_watchlist_view(self, res, res2):
        base = {
            "name": '%s - %d/%d' % (res["attributes"]['canonicalTitle'],
                                    res2["attributes"]['progress'],
                                    res["attributes"]['episodeCount'] if res["attributes"]['episodeCount'] is not None else 0),
            "url": "watchlist_query/%s/%s" % (res["attributes"]['canonicalTitle'], res["id"]),
            "image": res["attributes"]['posterImage']['medium'],
            "plot": res["attributes"]["synopsis"],
        }

        return self._parse_view(base)

class WonderfulSubsWLF(WatchlistFlavorBase):
    _TITLE = "WonderfulSubs"
    _NAME = "wonderfulsubs"

    @property
    def image(self):
        return self._login_image

    def login(self):
        r = requests.post('https://www.wonderfulsubs.com/api/users/login',
                          json={"username": self._username, "password": self._password})

        data = json.loads(r.text)

        if data['success'] is not True:
            return

        return self._format_login_data((data['data']['username']),
                                       (data['data']['profile_pic']),
                                       ('%s/%s' % (data['data']['_id'], data['token'])))

    def watchlist(self):
        url = 'https://www.wonderfulsubs.com/api/watchlist/list?_id=%s' % (self._login_token.split("/")[0])
        return self._process_watchlist_view(url, "watchlist/%d", page=1)

    def header(self):
        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(self._login_token.split("/")[1])
            }

        return header

    def _base_watchlist_view(self, res):
        result = []

        base = {
            "name": '%s' % (res['title']),
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

    def _process_watchlist_view(self, url, base_plugin_url, page):
        r = requests.get(url, headers=self.header())
        results = json.loads(r.text)['data']['watch_list']
        all_results = map(self._base_watchlist_view, results)
        all_results = list(itertools.chain(*all_results))
        return all_results

@route('watchlist_login/*')
def WL_LOGIN(payload, params):
    return WatchlistFlavor.login_request(payload.rsplit("/")[0])

@route('watchlist_logout')
def WL_LOGOUT(payload, params):
    return WatchlistFlavor.logout_request()

@route('watchlist')
def WATCHLIST(payload, params):
    return control.draw_items(WatchlistFlavor.watchlist_request())

@route('watchlist_status_type/*')
def WATCHLIST_STATUS_TYPE(payload, params):
    return control.draw_items(WatchlistFlavor.watchlist_status_request(payload.rsplit("/")[0]))

@route('watchlist_query/*')
def WATCHLIST_QUERY(payload, params):
    return control.draw_items(WonderfulSubsBrowser().search_site(payload.rsplit("/")[0]))

def add_watchlist(items):
    flavor = WatchlistFlavor.get_active_flavor()
    if not flavor:
        return

    items.insert(0, (
        "%s's %s" % (flavor.login_name, flavor.title),
        "watchlist",
        flavor.image,
    ))

    items.insert(len(items), (
        "Logout",
        "watchlist_logout",
        ''
    ))
