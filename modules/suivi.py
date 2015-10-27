import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

from nemubot.hooks import hook
from nemubot.exception import IRCException
from nemubot.tools.web import getURLContent
from more import Response

nemubotversion = 4.0

# POSTAGE SERVICE PARSERS ############################################

def get_colissimo_info(colissimo_id):
    colissimo_data = getURLContent("http://www.colissimo.fr/portail_colissimo/suivre.do?colispart=%s" % colissimo_id)
    soup = BeautifulSoup(colissimo_data)

    dataArray = soup.find(class_='dataArray')
    if dataArray and dataArray.tbody and dataArray.tbody.tr:
        date = dataArray.tbody.tr.find(headers="Date").get_text()
        libelle = dataArray.tbody.tr.find(headers="Libelle").get_text().replace('\n', '').replace('\t', '').replace('\r', '')
        site = dataArray.tbody.tr.find(headers="site").get_text().strip()
        return (date, libelle, site.strip())

def get_chronopost_info(track_id):
    data = urllib.parse.urlencode({'listeNumeros': track_id})
    track_baseurl = "http://www.chronopost.fr/expedier/inputLTNumbersNoJahia.do?lang=fr_FR"
    track_data = urllib.request.urlopen(track_baseurl, data.encode('utf-8'))
    soup = BeautifulSoup(track_data)

    infoClass = soup.find(class_='numeroColi2')
    if infoClass and infoClass.get_text():
        info = infoClass.get_text().split("\n")
        if len(info) >= 1:
            info = info[1].strip().split("\"")
            if len(info) >= 2:
                date = info[2]
                libelle = info[1]
                return (date, libelle)

def get_colisprive_info(track_id):
    data = urllib.parse.urlencode({'numColis': track_id})
    track_baseurl = "https://www.colisprive.com/moncolis/pages/detailColis.aspx"
    track_data = urllib.request.urlopen(track_baseurl, data.encode('utf-8'))
    soup = BeautifulSoup(track_data)

    dataArray = soup.find(class_='BandeauInfoColis')
    if dataArray and dataArray.find(class_='divStatut') and dataArray.find(class_='divStatut').find(class_='tdText'):
        status = dataArray.find(class_='divStatut').find(class_='tdText').get_text()
        return status

def get_laposte_info(laposte_id):
    data = urllib.parse.urlencode({'id': laposte_id})
    laposte_baseurl = "http://www.part.csuivi.courrier.laposte.fr/suivi/index"

    laposte_data = urllib.request.urlopen(laposte_baseurl, data.encode('utf-8'))
    soup = BeautifulSoup(laposte_data)
    search_res = soup.find(class_='resultat_rech_simple_table').tbody.tr
    if (soup.find(class_='resultat_rech_simple_table').thead
            and soup.find(class_='resultat_rech_simple_table').thead.tr
            and len(search_res.find_all('td')) > 3):
        field = search_res.find('td')
        poste_id = field.get_text()

        field = field.find_next('td')
        poste_type = field.get_text()

        field = field.find_next('td')
        poste_date = field.get_text()

        field = field.find_next('td')
        poste_location = field.get_text()

        field = field.find_next('td')
        poste_status = field.get_text()

        return (poste_type.lower(), poste_id.strip(), poste_status.lower(), poste_location, poste_date)


# TRACKING HANDLERS ###################################################

def handle_laposte(tracknum):
    info = get_laposte_info(tracknum)
    if info:
        poste_type, poste_id, poste_status, poste_location, poste_date = info
        return ("Le courrier de type \x02%s\x0F : \x02%s\x0F est actuellement \x02%s\x0F dans la zone \x02%s\x0F (Mis à jour le \x02%s\x0F)." % (poste_type, poste_id, poste_status, poste_location, poste_date))

def handle_colissimo(tracknum):
    info = get_colissimo_info(tracknum)
    if info:
        date, libelle, site = info
        return ("Colissimo: \x02%s\x0F : \x02%s\x0F Dernière mise à jour le \x02%s\x0F au site \x02%s\x0F." % (tracknum, libelle, date, site))

def handle_chronopost(tracknum):
    info = get_chronopost_info(tracknum)
    if info:
        date, libelle = info
        return ("Colis Chronopost: \x02%s\x0F : \x02%s\x0F. Dernière mise à jour \x02%s\x0F." % (tracknum, libelle, date))

def handle_coliprive(tracknum):
    info = get_colisprive_info(tracknum)
    if info:
        return ("Colis Privé: \x02%s\x0F : \x02%s\x0F." % (tracknum, info))

TRACKING_HANDLERS = {
    'laposte': handle_laposte,
    'colissimo': handle_colissimo,
    'chronopost': handle_chronopost,
    'coliprive': handle_coliprive
}

# HOOKS ##############################################################

@hook("cmd_hook", "track",
        help="Track postage",
        help_usage={"[@tracker] TRACKING_ID [TRACKING_ID ...]": "Track the specified postage IDs using the specified tracking service or all of them."})
def get_tracking_info(msg):
    if not len(msg.args):
        raise IRCException("Renseignez un identifiant d'envoi.")

    res = Response(channel=msg.channel, count=" (%d suivis supplémentaires)")

    if 'tracker' in msg.kwargs:
        if msg.kwargs['tracker'] in TRACKING_HANDLERS:
            trackers = {
                msg.kwargs['tracker']: TRACKING_HANDLERS[msg.kwargs['tracker']]
            }
        else:
            raise IRCException("No tracker named \x02{tracker}\x0F, please use one of the following: \x02{trackers}\x0F".format(tracker=msg.kwargs['tracker'], trackers=', '.join(TRACKING_HANDLERS.keys())))
    else:
        trackers = TRACKING_HANDLERS

    for tracknum in msg.args:
        for name,tracker in trackers.items():
            ret = tracker(tracknum)
            if ret:
                res.append_message(ret)
                break
        if not ret:
            res.append_message("L'identifiant \x02{id}\x0F semble incorrect, merci de vérifier son exactitude.".format(id=tracknum))
    return res
