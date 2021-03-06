# coding=utf-8

"""Send SMS using SMS API (currently only Free Mobile)"""

import re
import socket
import time
import urllib.error
import urllib.request
import urllib.parse

from nemubot import context
from nemubot.exception import IMException
from nemubot.hooks import hook
from nemubot.tools.xmlparser.node import ModuleState

nemubotversion = 3.4

from nemubot.module.more import Response

def load(context):
    context.data.setIndex("name", "phone")

def help_full():
    return "!sms /who/[,/who/[,...]] message: send a SMS to /who/."

def send_sms(frm, api_usr, api_key, content):
    content = "<%s> %s" % (frm, content)

    try:
        req = urllib.request.Request("https://smsapi.free-mobile.fr/sendmsg?user=%s&pass=%s&msg=%s" % (api_usr, api_key, urllib.parse.quote(content)))
        res = urllib.request.urlopen(req, timeout=5)
    except socket.timeout:
        return "timeout"
    except urllib.error.HTTPError as e:
        if e.code == 400:
            return "paramètre manquant"
        elif e.code == 402:
            return "paiement requis"
        elif e.code == 403 or e.code == 404:
            return "clef incorrecte"
        elif e.code != 200:
            return "erreur inconnue (%d)" % status
    except:
        return "unknown error"

    return None

def check_sms_dests(dests, cur_epoch):
    """Raise exception if one of the dest is not known or has already receive a SMS recently
    """
    for u in dests:
        if u not in context.data.index:
            raise IMException("Désolé, je sais pas comment envoyer de SMS à %s." % u)
        elif cur_epoch - float(context.data.index[u]["lastuse"]) < 42:
            raise IMException("Un peu de calme, %s a déjà reçu un SMS il n'y a pas si longtemps." % u)
    return True


def send_sms_to_list(msg, frm, dests, content, cur_epoch):
    fails = list()
    for u in dests:
        context.data.index[u]["lastuse"] = cur_epoch
        test = send_sms(frm, context.data.index[u]["user"], context.data.index[u]["key"], content)
        if test is not None:
            fails.append( "%s: %s" % (u, test) )

    if len(fails) > 0:
        return Response("quelque chose ne s'est pas bien passé durant l'envoi du SMS : " + ", ".join(fails), msg.channel, msg.frm)
    else:
        return Response("le SMS a bien été envoyé", msg.channel, msg.frm)


@hook.command("sms")
def cmd_sms(msg):
    if not len(msg.args):
        raise IMException("À qui veux-tu envoyer ce SMS ?")

    cur_epoch = time.mktime(time.localtime())
    dests = msg.args[0].split(",")
    frm = msg.frm if msg.to_response[0] == msg.frm else msg.frm + "@" + msg.to[0]
    content = " ".join(msg.args[1:])

    check_sms_dests(dests, cur_epoch)
    return send_sms_to_list(msg, frm, dests, content, cur_epoch)


@hook.command("smscmd")
def cmd_smscmd(msg):
    if not len(msg.args):
        raise IMException("À qui veux-tu envoyer ce SMS ?")

    cur_epoch = time.mktime(time.localtime())
    dests = msg.args[0].split(",")
    frm = msg.frm if msg.to_response[0] == msg.frm else msg.frm + "@" + msg.to[0]
    cmd = " ".join(msg.args[1:])

    content = None
    for r in context.subtreat(context.subparse(msg, cmd)):
        if isinstance(r, Response):
            for m in r.messages:
                if isinstance(m, list):
                    for n in m:
                        content = n
                        break
                    if content is not None:
                        break
                elif isinstance(m, str):
                    content = m
                    break

        elif isinstance(r, Text):
            content = r.message

    if content is None:
        raise IMException("Aucun SMS envoyé : le résultat de la commande n'a pas retourné de contenu.")

    check_sms_dests(dests, cur_epoch)
    return send_sms_to_list(msg, frm, dests, content, cur_epoch)


apiuser_ask = re.compile(r"(utilisateur|user|numéro|numero|compte|abonne|abone|abonné|account)\s+(est|is)\s+(?P<user>[0-9]{7,})", re.IGNORECASE)
apikey_ask = re.compile(r"(clef|key|password|mot de passe?)\s+(?:est|is)?\s+(?P<key>[a-zA-Z0-9]{10,})", re.IGNORECASE)

@hook.ask()
def parseask(msg):
    if msg.message.find("Free") >= 0 and (
            msg.message.find("API") >= 0 or msg.message.find("api") >= 0) and (
                msg.message.find("SMS") >= 0 or msg.message.find("sms") >= 0):
        resuser = apiuser_ask.search(msg.message)
        reskey = apikey_ask.search(msg.message)
        if resuser is not None and reskey is not None:
            apiuser = resuser.group("user")
            apikey = reskey.group("key")

            test = send_sms("nemubot", apiuser, apikey,
                            "Vous avez enregistré vos codes d'authentification dans nemubot, félicitation !")
            if test is not None:
                return Response("je n'ai pas pu enregistrer tes identifiants : %s" % test, msg.channel, msg.frm)

            if msg.frm in context.data.index:
                context.data.index[msg.frm]["user"] = apiuser
                context.data.index[msg.frm]["key"] = apikey
            else:
                ms = ModuleState("phone")
                ms.setAttribute("name", msg.frm)
                ms.setAttribute("user", apiuser)
                ms.setAttribute("key", apikey)
                ms.setAttribute("lastuse", 0)
                context.data.addChild(ms)
            context.save()
            return Response("ok, c'est noté. Je t'ai envoyé un SMS pour tester ;)",
                            msg.channel, msg.frm)
