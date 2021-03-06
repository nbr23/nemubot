import urllib

from nemubot.tools.web import getNormalizedURL, getJSON

def isup(url):
    """Determine if the given URL is up or not

    Argument:
    url -- the URL to check
    """

    o = urllib.parse.urlparse(getNormalizedURL(url), "http")
    if o.netloc != "":
        isup = getJSON("https://isitup.org/%s.json" % o.netloc)
        if isup is not None and "status_code" in isup and isup["status_code"] == 1:
            return isup["response_time"]

    return None
