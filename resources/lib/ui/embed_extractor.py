import re
import urllib
import urlparse
import utils
import http
import requests
import json
import time
from bs4 import BeautifulSoup

_EMBED_EXTRACTORS = {}

def load_video_from_url(in_url):
    found_extractor = None

    for extractor in _EMBED_EXTRACTORS.keys():
        if in_url.startswith(extractor):
            found_extractor = _EMBED_EXTRACTORS[extractor]
            break

    if found_extractor is None:
        print "[*E*] No extractor found for %s" % in_url
        return None

    try:
        if found_extractor['preloader'] is not None:
            print "Modifying Url: %s" % in_url
            in_url = found_extractor['preloader'](in_url)

        data = found_extractor['data']
        if data is not None:
            return found_extractor['parser'](in_url,
                                             data)

        print "Probing source: %s" % in_url
        reqObj = http.send_request(in_url)
        return found_extractor['parser'](http.raw_url(reqObj.url),
                                         reqObj.text,
                                         http.get_referer(in_url))
    except http.URLError:
        return None # Dead link, Skip result
    except:
        raise

    return None

def __check_video_list(refer_url, vidlist, add_referer=False,
                       ignore_cookie=False):
    nlist = []
    for item in vidlist:
        try:
            item_url = item[1]
            if add_referer:
                item_url = http.add_referer_url(item_url, refer_url)

            temp_req = http.head_request(item_url)
            if temp_req.status_code != 200:
                print "[*] Skiping Invalid Url: %s - status = %d" % (item[1],
                                                             temp_req.status_code)
                continue # Skip Item.

            out_url = temp_req.url
            if ignore_cookie:
                out_url = http.strip_cookie_url(out_url)

            nlist.append((item[0], out_url, item[2]))
        except Exception, e:
            # Just don't add source.
            pass

    return nlist

def __extract_wonderfulsubs(url, content, referer=None):
    res = json.loads(content)
    if res["status"] != 200:
        raise Exception("Failed with error code of %d" % res["status"])

    if res.has_key("embed"):
        embed_url = res["embed"]
        return load_video_from_url(embed_url)

    results = __check_video_list(url,
                                 map(lambda x: (x['label'],
                                                x['src'],
                                                x['captions']['src'] if x.has_key('captions') else None), res["urls"]))

    return results

def __extract_rapidvideo(url, page_content, referer=None):
    soup = BeautifulSoup(page_content, 'html.parser')
    results = map(lambda x: (x['label'], x['src']),
                  soup.select('source'))
    return results

def __extract_mp4upload(url, page_content, referer=None):
    SOURCE_RE_1 = re.compile(r'.*?\|IFRAME\|(\d+)\|.*?\|\d+\|false\|h1\|w1\|(.*?)\|.*?',
                             re.DOTALL)
    SOURCE_RE_2 = re.compile(r'.*?\|video\|(.*?)\|(\d+)\|.*?',
                             re.DOTALL)
    label, domain = SOURCE_RE_1.match(page_content).groups()
    video_id, protocol = SOURCE_RE_2.match(page_content).groups()
    stream_url = 'https://{}.mp4upload.com:{}/d/{}/video.mp4'
    stream_url = stream_url.format(domain, protocol, video_id)
    stream = [(label, stream_url)]
    return stream

def __extract_xstreamcdn(url, data):
    res = requests.post(url, data=data)
    res = res.json()['data']
    results = map(lambda x: (x['label'], x['file']), res)
    return results

def __register_extractor(urls, function, url_preloader=None, data=None):
    if type(urls) is not list:
        urls = [urls]

    for url in urls:
        _EMBED_EXTRACTORS[url] = {
            "preloader": url_preloader,
            "parser": function,
            "data": data
        }

def __ignore_extractor(url, content, referer=None):
    return None

def __relative_url(original_url, new_url):
    if new_url.startswith("http://") or new_url.startswith("https://"):
        return new_url

    if new_url.startswith("//"):
        return "http:%s" % new_url
    else:
        return urlparse.urljoin(original_url, new_url)

def __extractor_factory(regex, double_ref=False, match=0, debug=False):
    compiled_regex = re.compile(regex, re.DOTALL)

    def f(url, content, referer=None):
        if debug:
            print url
            print content
            print compiled_regex.findall(content)
            raise

        try:
            regex_url = compiled_regex.findall(content)[match]
            regex_url = __relative_url(url, regex_url)
            if double_ref:
                video_url = utils.head_request(http.add_referer_url(regex_url, url)).url
            else:
                video_url = __relative_url(regex_url, regex_url)
            return video_url
        except Exception, e:
            print "[*E*] Failed to load link: %s: %s" % (url, e)
            return None
    return f

__register_extractor(["https://www.wonderfulsubs.com/api/media/stream"],
                     __extract_wonderfulsubs)

__register_extractor(["https://www.rapidvideo.com/e/",
                      "https://www.rapidvid.to/e/"],
                     __extract_rapidvideo,
                     lambda x: x.replace('/e/', '/v/'))

__register_extractor(["http://mp4upload.com/",
                      "http://www.mp4upload.com/",
                      "https://www.mp4upload.com/",
                      "https://mp4upload.com/"],
                     __extract_mp4upload)

__register_extractor(["https://www.xstreamcdn.com/v/"],
                     __extract_xstreamcdn,
                     lambda x: x.replace('/v/', '/api/source/'),
                     {'d': 'www.xstreamcdn.com'})

__register_extractor(["https://gcloud.live/v/"],
                     __extract_xstreamcdn,
                     lambda x: x.replace('/v/', '/api/source/'),
                     {'d': 'gcloud.live'})

__register_extractor(["https://www.fembed.com/v/"],
                     __extract_xstreamcdn,
                     lambda x: x.replace('/v/', '/api/source/'),
                     {'d': 'www.fembed.com'})
