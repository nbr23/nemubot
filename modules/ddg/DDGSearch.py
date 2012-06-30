# coding=utf-8

import http.client
import re
from urllib.parse import quote

import module_states_file as xmlparser

class DDGSearch:
  def __init__(self, terms):
    self.terms = terms
    self.curRT = -1
    (res, page) = getPage(terms)
    if res == http.client.OK:
      self.ddgres = xmlparser.parse_string(page)
    else:
      self.ddgres = None

  @property
  def type(self):
    return self.ddgres.getFirstNode("Type").getContent()

  @property
  def definition(self):
    if self.ddgres.hasNode("Definition"):
      return self.ddgres.getFirstNode("Definition").getContent()
    else:
      return "Sorry, no definition found for %s" % self.terms

  @property
  def nextRes(self):
    if self.type == "D":
      if len(self.ddgres.getFirstNode("RelatedTopics").getNodes("RelatedTopic")) > self.curRT + 1:
        self.curRT += 1
        node = self.ddgres.getFirstNode("RelatedTopics").getNodes("RelatedTopic")[self.curRT]
        return node.getFirstNode("Text").getContent()
    elif self.ddgres.hasNode("Answer"):
      if self.curRT < 0:
        self.curRT = 0
        return striphtml(self.ddgres.getFirstNode("Answer").getContent())
    elif self.ddgres.hasNode("Abstract") and len (self.ddgres.getNode("Abstract").getContent()) > 0:
      if self.curRT < 0:
        self.curRT = 0
        return self.ddgres.getNode("Abstract").getContent() + " <" + self.ddgres.getNode("AbstractURL").getContent() + ">"
      elif len(self.ddgres.getFirstNode("RelatedTopics").getNodes("RelatedTopic")) > self.curRT:
        node = self.ddgres.getFirstNode("RelatedTopics").getNodes("RelatedTopic")[self.curRT]
        self.curRT += 1
        return node.getFirstNode("Text").getContent()
    return "No more results"


def striphtml(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def getPage(terms):
  conn = http.client.HTTPConnection("api.duckduckgo.com")
  try:
    conn.request("GET", "/?q=%s&format=xml" % quote(terms))
  except socket.gaierror:
    print ("impossible de récupérer la page %s."%(p))
    return (http.client.INTERNAL_SERVER_ERROR, None)

  res = conn.getresponse()
  data = res.read()

  conn.close()
  return (res.status, data)
