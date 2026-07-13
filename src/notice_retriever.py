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
NOTICE_FEED_URL_START = "https://www.thegazette.co.uk/all-notices/"
NOTICE_FEED_URL_END = "/notice/data.feed?categorycode-all=all&numberOfLocationSearches=1&location-distance-1=1&sort-by=latest-date&noticetypes=1101"
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
            "Request for notice '%s' failed (status code %d, response prefix %r)",
            notice_id,
            res.status,
            res.data[:1000],
        )
        raise Exception("Request for notice did not succeed")

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
        feed_url = (
            f"{NOTICE_FEED_URL_START}{gazette}{NOTICE_FEED_URL_END}"
            f"&editon={gazette}&text={query}&results-page-size={PAGE_SIZE}"
            f"&results-page={page_number}"
        )
        res = http.request(
            "GET",
            feed_url,
            headers=HTTP_HEADERS,
            timeout=4.0,
            retries=HTTP_RETRIES,
        )

        # Raise an exception if we get a bad status code
        if res.status != 200:
            logging.error(
                "Request for %s Gazette feed page %d failed "
                "(status code %d, response prefix %r)",
                gazette,
                page_number,
                res.status,
                res.data[:1000],
            )
            raise Exception("Request for Gazette feed did not succeed")

        # Parse the result as XML
        soup = BeautifulSoup(res.data, "xml")
        feed = soup.feed
        if feed is None:
            logging.error(
                "Response for %s Gazette feed page %d did not contain a feed "
                "element (response prefix %r)",
                gazette,
                page_number,
                res.data[:1000],
            )
            raise Exception("Could not find feed in response")
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
        if page_stop is None or page_total is None:
            logging.error(
                "Response for %s Gazette feed page %d omitted pagination "
                "metadata (page-stop=%r, total=%r)",
                gazette,
                page_number,
                page_stop,
                page_total,
            )
            raise Exception("Could not find feed pagination metadata")
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
