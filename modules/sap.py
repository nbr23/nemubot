# coding=utf-8

"""Find information about an SAP transaction codes"""

import re
import urllib.parse

from nemubot.exception import IRCException
from nemubot.hooks import hook
from nemubot.tools import web
from nemubot.tools.web import striphtml

nemubotversion = 3.4

from more import Response


def help_full():
    return "!tcode <transaction code|keywords>"


@hook("cmd_hook", "tcode")
def cmd_tcode(msg):
    if len(msg.cmds) != 2:
        raise IRCException("indicate a transaction code or "
                           "a keyword to search!")

    url = ("http://www.tcodesearch.com/tcodes/search?q=%s" %
           urllib.parse.quote(msg.cmds[1]))
    page = web.getURLContent(url)

    res = Response(channel=msg.channel,
                   nomore="No more transaction code",
                   count=" (%d more tcodes)")

    if page is not None:
        index = (page.index('<div id="searchresults">') +
                 len('<div id="searchresults">'))
        end = page[index:].index('</div>')+index
        strscope = page[index:end]
        for tcode in re.finditer('<strong> ([a-zA-Z0-9_]*)</strong> - ([^\n]*)\n', strscope):
            res.append_message("\x02%s\x0F - %s" % (tcode.group(1),
                                                    striphtml(tcode.group(2))))

    return res
