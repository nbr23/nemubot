# coding=utf-8

import http.client
import re
import socket
import json
from urllib.parse import quote

nemubotversion = 3.2

import xmlparser

LANG = ["ar", "zh", "cz", "en", "fr", "gr", "it",
        "ja", "ko", "pl", "pt", "ro", "es", "tr"]

def load(context):
    from hooks import Hook
    context.hooks.add_hook(context.hooks.cmd_hook,
                           Hook(cmd_translate, "translate"))
    context.hooks.add_hook(context.hooks.cmd_hook,
                           Hook(cmd_translate, "traduction"))
    context.hooks.add_hook(context.hooks.cmd_hook,
                           Hook(cmd_translate, "traduit"))
    context.hooks.add_hook(context.hooks.cmd_hook,
                           Hook(cmd_translate, "traduire"))


def cmd_translate(msg):
    global LANG
    startWord = 1
    if msg.cmd[startWord] in LANG:
        langTo = msg.cmd[startWord]
        startWord += 1
    else:
        langTo = "fr"
        if msg.cmd[startWord] in LANG:
            langFrom = langTo
            langTo = msg.cmd[startWord]
            startWord += 1
        else:
            if langTo == "en":
                langFrom = "fr"
            else:
                langFrom = "en"

    (res, page) = getPage(' '.join(msg.cmd[startWord:]), langFrom, langTo)
    if res == http.client.OK:
        wres = json.loads(page.decode())
        if "Error" in wres:
            return Response(msg.sender, wres["Note"], msg.channel)
        else:
            start = "Traduction de %s : "%' '.join(msg.cmd[startWord:])
            if "Entries" in wres["term0"]:
                if "SecondTranslation" in wres["term0"]["Entries"]["0"]:
                    return Response(msg.sender, start +
                                    wres["term0"]["Entries"]["0"]["FirstTranslation"]["term"] +
                                    " ; " +
                                    wres["term0"]["Entries"]["0"]["SecondTranslation"]["term"],
                                    msg.channel)
                else:
                    return Response(msg.sender, start +
                                    wres["term0"]["Entries"]["0"]["FirstTranslation"]["term"],
                                    msg.channel)
            elif "PrincipalTranslations" in wres["term0"]:
                if "1" in wres["term0"]["PrincipalTranslations"]:
                    return Response(msg.sender, start +
                                    wres["term0"]["PrincipalTranslations"]["0"]["FirstTranslation"]["term"] +
                                    " ; " +
                                    wres["term0"]["PrincipalTranslations"]["1"]["FirstTranslation"]["term"],
                                    msg.channel)
                else:
                    return Response(msg.sender, start +
                                    wres["term0"]["PrincipalTranslations"]["0"]["FirstTranslation"]["term"],
                                    msg.channel)
            else:
                return Response(msg.sender, "Une erreur s'est produite durant la recherche"
                                " d'une traduction de %s"
                                % ' '.join(msg.cmd[startWord:]),
                                msg.channel)


def getPage(terms, langfrom="fr", langto="en"):
    conn = http.client.HTTPConnection("api.wordreference.com", timeout=5)
    try:
        conn.request("GET", "/0.8/%s/json/%s%s/%s" % (
                CONF.getNode("wrapi")["key"], langfrom, langto, quote(terms)))
    except socket.gaierror:
        print ("impossible de récupérer la page WordReference.")
        return (http.client.INTERNAL_SERVER_ERROR, None)
    except (TypeError, KeyError):
        print ("You need a WordReference API key in order to use this module."
               " Add it to the module configuration file:\n<wrapi key=\"XXXXX\""
               " />\nRegister at "
               "http://www.wordreference.com/docs/APIregistration.aspx")
        return (http.client.INTERNAL_SERVER_ERROR, None)

    res = conn.getresponse()
    data = res.read()

    conn.close()
    return (res.status, data)
