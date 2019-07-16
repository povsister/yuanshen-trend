from http.cookiejar import MozillaCookieJar
import urllib3
from gzip import decompress
from urllib.parse import urlparse, parse_qsl
import traceback
from bs4 import BeautifulSoup
from warnings import filterwarnings
from re import compile, sub
from datetime import datetime, date


def html2Text(html):
    filterwarnings('ignore', category=UserWarning, module='bs4')
    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text()
    regex = compile(u'(\xa0|\xa01|\xa02|\xa03|\xa04|\ufeff|\n)')
    text = sub(regex, u' ', text).strip()
    return text


def remove_url(text):
    regex = compile(u'(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]')
    return sub(regex, u'', text)


def get_query_as_dict(path):
    o = urlparse(path)
    query = dict(parse_qsl(o.query))
    return query


def day_sub(dtm, day):
    dtm = dtm.timestamp()
    secs = day * 24 * 3600
    dt = dtm - secs
    return dt


def get_today_datetime():
    dt = date.today()
    return datetime(dt.year, dt.month, dt.day, 0, 0, 0)


def get_urlopener_with_cookie(cookie):
    urllib3.disable_warnings()
    # pre-defined header
    headers = {
        'Accept-Encoding': 'gzip, deflate, br',
        'User-Agent': 'okhttp/3.10.0',
        'Connection': 'keep-alive'
    }
    # Cookie processor
    if cookie is not None:
        ck = MozillaCookieJar()
        ck.load(cookie)
        ck_list = []
        for i in ck:
            ck_list.append(i.name + '=' + i.value)
        ck_header = '; '.join(ck_list)
        headers['Cookie'] = ck_header
        hp = urllib3.PoolManager(headers=headers)
    else:
        hp = urllib3.PoolManager()

    return hp


def unzip(resp):
    try:
        return decompress(resp)
    except Exception:
        traceback.print_exc()
        return ''


def get_response(opener, url, method='GET', retries=3):
    try:
        res = opener.urlopen(method, url, retries=retries)
        return res.data.decode('utf8')
    except Exception:
        return ''
