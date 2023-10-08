# requirements: lxml, beautifulsoup4

import urllib3
from urllib3.util import Retry
import urllib.parse
from bs4 import BeautifulSoup
import logging

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
)
NOTICE_URL = "https://www.thegazette.co.uk/notice/"
NOTICE_FEED_URL = "https://www.thegazette.co.uk/all-notices/notice/data.feed?categorycode-all=all&numberOfLocationSearches=1&location-distance-1=1&sort-by=latest-date&noticetypes=1101"
PAGE_SIZE = 5

HTTP_RETRIES = Retry(
    total=10,
    redirect=5,
    backoff_factor=0.1,
    status_forcelist=[500, 502, 503, 504, 506],
)
HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
}


def fetch_notice(http: urllib3.PoolManager, notice_id: str) -> str:
    res = http.request(
        "GET",
        f"{NOTICE_URL}{notice_id}/data.xml",
        headers=HTTP_HEADERS,
        timeout=4.0,
        retries=HTTP_RETRIES,
    )

    # Raise an exception if we get a bad status code
    if res.status != 200:
        logging.error(
            "Request for feed did not succeed (status code %d, response data %b)",
            res.status,
            res.data,
        )
        raise Exception("Request for feed did not succeed")

    # Parse the result as XML
    soup = BeautifulSoup(res.data, "xml")
    logging.debug("Notice '%s': '%s'", notice_id, str(soup))

    # Find the element containing the notice text
    textEl = soup.find("div", {"about": "this:notifiableThing"}) or soup.find(
        "div", {"class": "content"}
    )
    if not textEl:
        logging.error("Could not find notice text within notice xml: %s", str(soup))
        raise Exception("Could not find notice text within notice xml")

    text = textEl.text
    text = " ".join(text.split())  # Remove excessive whitespace
    return text


def fetch_all_notices(http: urllib3.PoolManager, gazette: str, query: str, callback):
    logging.debug(
        "Fetching feed from gazette '%s', with query '%s', and page sizes of %d",
        gazette,
        query,
        PAGE_SIZE,
    )

    # URL encode for addition to the URL
    query = urllib.parse.quote_plus(query)

    page_number = 1
    while True:
        logging.debug("Fetching page %d of feed", page_number)
        res = http.request(
            "GET",
            f"{NOTICE_FEED_URL}&editon={gazette}&text={query}&results-page-size={PAGE_SIZE}&results-page={page_number}",
            headers=HTTP_HEADERS,
            timeout=4.0,
            retries=HTTP_RETRIES,
        )

        # Raise an exception if we get a bad status code
        if res.status != 200:
            logging.error(
                "Request for feed did not succeed (status code %d, response data %b)",
                res.status,
                res.data,
            )
            raise Exception("Request for feed did not succeed")

        # Parse the result as XML
        soup = BeautifulSoup(res.data, "xml")
        feed = soup.feed
        logging.debug("Page %d of feed: %s", page_number, str(soup))

        page_stop = None
        page_total = None
        for item in feed.children:
            if item.name == "entry":
                item = {"id": item.id.string}
                callback(item)
            elif item.name == "page-stop" or item.name == "f:page-stop":
                page_stop = item
            elif item.name == "total" or item.name == "f:total":
                page_total = item

        # Check if there are any more pages
        page_stop = int(page_stop.string)
        page_total = int(page_total.string)
        if page_stop >= page_total:
            break
        else:
            page_number += 1


def get_notice_text(http: urllib3.PoolManager, notice_id) -> str:
    # The "id" field contains the notice id, but it is within a URL - have to remove the URL part before it
    ID_PREFIX = "https://www.thegazette.co.uk/id/notice/"
    id = notice_id
    if id.startswith(ID_PREFIX):
        id = id[len(ID_PREFIX) :]
    else:
        logging.error("Unable to get notice id: %s", id)
        raise Exception("Unable to get notice id")

    text = fetch_notice(http, id)
    logging.debug("Fetched notice: %s", text)

    return text
