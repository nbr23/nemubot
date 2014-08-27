# coding=utf-8

"""Repositories, users or issues on GitHub"""

import json
import re
import urllib.error
from urllib.parse import quote
from urllib.request import urlopen

from hooks import hook

nemubotversion = 3.4

def help_full ():
    return "!github /repo/: Display information about /repo/.\n!github_user /user/: Display information about /user/."



def info_repos(repo):
    raw = urlopen("https://api.github.com/search/repositories?q=%s" % quote(repo), timeout=10)
    return json.loads(raw.read().decode())

def info_user(username):
    raw = urlopen("https://api.github.com/users/%s" % quote(username), timeout=10)
    user = json.loads(raw.read().decode())

    raw = urlopen("https://api.github.com/users/%s/repos?sort=updated" % quote(username), timeout=10)
    user["repos"] = json.loads(raw.read().decode())

    return user

def info_issue(repo, issue=None):
    rp = info_repos(repo)
    if rp["items"]:
        fullname = rp["items"][0]["full_name"]
    else:
        fullname = repo

    try:
        if issue is not None:
            raw = urlopen("https://api.github.com/repos/%s/issues/%s" % (quote(fullname), quote(issue)), timeout=10)
            return [ json.loads(raw.read().decode()) ]
        else:
            raw = urlopen("https://api.github.com/repos/%s/issues?sort=updated" % quote(fullname), timeout=10)
            return json.loads(raw.read().decode())
    except urllib.error.HTTPError:
        raise IRCException("Repository not found")


@hook("cmd_hook", "github")
def cmd_github(msg):
    if len(msg.cmds) < 2:
        raise IRCException("indicate a repository name to search")

    repos = info_repos(" ".join(msg.cmds[1:]))

    res = Response(msg.sender, channel=msg.channel, nomore="No more repository", count=" (%d more repo)")

    for repo in repos["items"]:
        homepage = ""
        if repo["homepage"] is not None:
            homepage = repo["homepage"] + " - "
        res.append_message("Repository %s: %s%s Main language: %s; %d forks; %d stars; %d watchers; %d opened_issues; view it at %s" % (repo["full_name"], homepage, repo["description"], repo["language"], repo["forks"], repo["stargazers_count"], repo["watchers_count"], repo["open_issues_count"], repo["html_url"]))

    return res

@hook("cmd_hook", "github_user")
def cmd_github(msg):
    if len(msg.cmds) < 2:
        raise IRCException("indicate a user name to search")

    res = Response(msg.sender, channel=msg.channel, nomore="No more user")

    user = info_user(" ".join(msg.cmds[1:]))

    if "login" in user:
        if user["repos"]:
            kf = " Known for: " + ", ".join([repo["name"] for repo in user["repos"]])
        else:
            kf = ""
        if "name" in user:
            name = user["name"]
        else:
            name = user["login"]
        res.append_message("User %s: %d public repositories; %d public gists; %d followers; %d following; view it at %s.%s" % (name, user["public_repos"], user["public_gists"], user["followers"], user["following"], user["html_url"], kf))
    else:
        raise IRCException("User not found")

    return res


@hook("cmd_hook", "github_issue")
def cmd_github(msg):
    if len(msg.cmds) < 2:
        raise IRCException("indicate a user name to search")

    repo = " ".join(msg.cmds[1:])
    li = re.match("^(?P<repo>.*)\s+(?:#(?P<issue>[0-9]+))$", repo)
    ri = re.match("^(?:#(?P<issue>[0-9]+))\s+(?P<repo>.*)$", repo)

    if li is not None:
        issue = li.group("issue")
        repo = li.group("repo")
        count = None
    elif ri is not None:
        issue = ri.group("issue")
        repo = ri.group("repo")
        count = None
    else:
        issue = None
        count = " (%d more issues)"

    res = Response(msg.sender, channel=msg.channel, nomore="No more issue", count=count)

    issues = info_issue(repo, issue)

    for issue in issues:
        res.append_message("%s%s issue #%d: \x03\x02%s\x03\x02 opened by %s on %s: %s" % (issue["state"][0].upper(), issue["state"][1:], issue["number"], issue["title"], issue["user"]["login"], issue["created_at"], issue["body"].replace("\n", " ")))

    return res
