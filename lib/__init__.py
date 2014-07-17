# -*- coding: utf-8 -*-

# Nemubot is a smart and modulable IM bot.
# Copyright (C) 2012-2014  nemunaire
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from datetime import timedelta
from queue import Queue
import threading
import time
import re

from nemubot import consumer
from nemubot import event
from nemubot import hooks
from nemubot.networkbot import NetworkBot
from nemubot.IRCServer import IRCServer
from nemubot.DCC import DCC
from nemubot import response

ID_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

class Bot:
    def __init__(self, ip, realname, mp=list()):
        # Bot general informations
        self.version     = 4.0
        self.version_txt = '4.0.dev0'

        # Save various informations
        self.ip = ip
        self.realname = realname
        self.ctcp_capabilities = dict()
        self.init_ctcp_capabilities()

        # Keep global context: servers and modules
        self.servers = dict()
        self.modules = dict()

        # Context paths
        self.modules_path = mp
        self.datas_path   = './datas/'

        # Events
        self.events      = list()
        self.event_timer = None

        # Own hooks
        self.hooks       = hooks.MessagesHook(self, self)

        # Other known bots, making a bots network
        self.network     = dict()
        self.hooks_cache = dict()

        # Messages to be treated
        self.cnsr_queue     = Queue()
        self.cnsr_thrd      = list()
        self.cnsr_thrd_size = -1

        self.hooks.add_hook("irc_hook",
                            hooks.Hook(self.treat_prvmsg, "PRIVMSG"),
                            self)


    def init_ctcp_capabilities(self):
        """Reset existing CTCP capabilities to default one"""
        self.ctcp_capabilities["ACTION"] = lambda srv, msg: print ("ACTION receive")
        self.ctcp_capabilities["CLIENTINFO"] = self._ctcp_clientinfo
        self.ctcp_capabilities["DCC"] = self._ctcp_dcc
        self.ctcp_capabilities["NEMUBOT"] = lambda srv, msg: _ctcp_response(
                                       msg.sender, "NEMUBOT %f" % self.version)
        self.ctcp_capabilities["TIME"] = lambda srv, msg: _ctcp_response(
                                      msg.sender, "TIME %s" % (datetime.now()))
        self.ctcp_capabilities["USERINFO"] = lambda srv, msg: _ctcp_response(
                                     msg.sender, "USERINFO %s" % self.realname)
        self.ctcp_capabilities["VERSION"] = lambda srv, msg: _ctcp_response(
                          msg.sender, "VERSION nemubot v%s" % self.version_txt)

    def _ctcp_clientinfo(self, srv, msg):
        """Response to CLIENTINFO CTCP message"""
        return _ctcp_response(msg.sndr,
                              " ".join(self.ctcp_capabilities.keys()))

    def _ctcp_dcc(self, srv, msg):
        """Response to DCC CTCP message"""
        ip = srv.toIP(int(msg.cmds[3]))
        conn = DCC(srv, msg.sender)
        if conn.accept_user(ip, int(msg.cmds[4])):
            srv.dcc_clients[conn.sender] = conn
            conn.send_dcc("Hello %s!" % conn.nick)
        else:
            print ("DCC: unable to connect to %s:%s" % (ip, msg.cmds[4]))


    def add_event(self, evt, eid=None, module_src=None):
        """Register an event and return its identifiant for futur update"""
        if eid is None:
            # Find an ID
            now = datetime.now()
            evt.id = "%d%c%d%d%c%d%d%c%d" % (now.year, ID_letters[now.microsecond % 52],
                                             now.month, now.day, ID_letters[now.microsecond % 42],
                                             now.hour, now.minute, ID_letters[now.microsecond % 32],
                                             now.second)
        else:
            evt.id = eid

        # Add the event in place
        t = evt.current
        i = -1
        for i in range(0, len(self.events)):
            if self.events[i].current > t:
                i -= 1
                break
        self.events.insert(i + 1, evt)
        if i == -1:
            self.update_timer()
            if len(self.events) <= 0 or self.events[i+1] != evt:
                return None

        if module_src is not None:
            module_src.REGISTERED_EVENTS.append(evt.id)

        return evt.id

    def del_event(self, id, module_src=None):
        """Find and remove an event from list"""
        if len(self.events) > 0 and id == self.events[0].id:
            self.events.remove(self.events[0])
            self.update_timer()
            if module_src is not None:
                module_src.REGISTERED_EVENTS.remove(evt.id)
            return True

        for evt in self.events:
            if evt.id == id:
                self.events.remove(evt)

                if module_src is not None:
                    module_src.REGISTERED_EVENTS.remove(evt.id)
                return True
        return False

    def update_timer(self):
        """Relaunch the timer to end with the closest event"""
        # Reset the timer if this is the first item
        if self.event_timer is not None:
            self.event_timer.cancel()
        if len(self.events) > 0:
            #print ("Update timer, next in", self.events[0].time_left.seconds,
            #       "seconds")
            if datetime.now() + timedelta(seconds=5) >= self.events[0].current:
                while datetime.now() < self.events[0].current:
                    time.sleep(0.6)
                self.end_timer()
            else:
                self.event_timer = threading.Timer(
                    self.events[0].time_left.seconds + 1, self.end_timer)
                self.event_timer.start()
        #else:
        #    print ("Update timer: no timer left")

    def end_timer(self):
        """Function called at the end of the timer"""
        #print ("end timer")
        while len(self.events)>0 and datetime.now() >= self.events[0].current:
            #print ("end timer: while")
            evt = self.events.pop(0)
            self.cnsr_queue.put_nowait(consumer.EventConsumer(evt))
            self.update_consumers()

        self.update_timer()


    def addServer(self, node, nick, owner, realname, ssl=False):
        """Add a new server to the context"""
        srv = IRCServer(node, nick, owner, realname, ssl)
        srv.add_hook = lambda h: self.hooks.add_hook("irc_hook", h, self)
        srv.add_networkbot = self.add_networkbot
        srv.send_bot = lambda d: self.send_networkbot(srv, d)
        srv.register_hooks()
        if srv.id not in self.servers:
            self.servers[srv.id] = srv
            if srv.autoconnect:
                srv.launch(self.receive_message)
            return True
        else:
            return False


    def add_module(self, module):
        """Add a module to the context, if already exists, unload the
        old one before"""
        # Check if the module already exists
        for mod in self.modules.keys():
            if self.modules[mod].name == module.name:
                self.unload_module(self.modules[mod].name)
                break

        self.modules[module.name] = module
        return True


    def add_modules_path(self, path):
        """Add a path to the modules_path array, used by module loader"""
        # The path must end by / char
        if path[len(path)-1] != "/":
            path = path + "/"

        if path not in self.modules_path:
            self.modules_path.append(path)
            return True

        return False


    def unload_module(self, name, verb=False):
        """Unload a module"""
        if name in self.modules:
            print (name)
            self.modules[name].save()
            if hasattr(self.modules[name], "unload"):
                self.modules[name].unload(self)
            # Remove registered hooks
            for (s, h) in self.modules[name].REGISTERED_HOOKS:
                self.hooks.del_hook(s, h)
            # Remove registered events
            for e in self.modules[name].REGISTERED_EVENTS:
                self.del_event(e)
            # Remove from the dict
            del self.modules[name]
            return True
        return False

    def update_consumers(self):
        """Launch new consumer thread if necessary"""
        if self.cnsr_queue.qsize() > self.cnsr_thrd_size:
            c = consumer.Consumer(self)
            self.cnsr_thrd.append(c)
            c.start()
            self.cnsr_thrd_size += 2


    def receive_message(self, srv, raw_msg, private=False, data=None):
        """Queued the message for treatment"""
        #print (raw_msg)
        self.cnsr_queue.put_nowait(consumer.MessageConsumer(srv, raw_msg, datetime.now(), private, data))

        # Launch a new thread if necessary
        self.update_consumers()


    def add_networkbot(self, srv, dest, dcc=None):
        """Append a new bot into the network"""
        id = srv.id + "/" + dest
        if id not in self.network:
            self.network[id] = NetworkBot(self, srv, dest, dcc)
        return self.network[id]

    def send_networkbot(self, srv, cmd, data=None):
        for bot in self.network:
            if self.network[bot].srv == srv:
                self.network[bot].send_cmd(cmd, data)

    def quit(self, verb=False):
        """Save and unload modules and disconnect servers"""
        if self.event_timer is not None:
            if verb: print ("Stop the event timer...")
            self.event_timer.cancel()

        if verb: print ("Save and unload all modules...")
        k = list(self.modules.keys())
        for mod in k:
            self.unload_module(mod, verb)

        if verb: print ("Close all servers connection...")
        k = list(self.servers.keys())
        for srv in k:
            self.servers[srv].disconnect()

# Hooks cache

    def create_cache(self, name):
        if name not in self.hooks_cache:
            if isinstance(self.hooks.__dict__[name], list):
                self.hooks_cache[name] = list()

                # Start by adding locals hooks
                for h in self.hooks.__dict__[name]:
                    tpl = (h, 0, self.hooks.__dict__[name], self.hooks.bot)
                    self.hooks_cache[name].append(tpl)

                # Now, add extermal hooks
                level = 0
                while level == 0 or lvl_exist:
                    lvl_exist = False
                    for ext in self.network:
                        if len(self.network[ext].hooks) > level:
                            lvl_exist = True
                            for h in self.network[ext].hooks[level].__dict__[name]:
                                if h not in self.hooks_cache[name]:
                                    self.hooks_cache[name].append((h, level + 1,
                                                                   self.network[ext].hooks[level].__dict__[name], self.network[ext].hooks[level].bot))
                    level += 1

            elif isinstance(self.hooks.__dict__[name], dict):
                self.hooks_cache[name] = dict()

                # Start by adding locals hooks
                for h in self.hooks.__dict__[name]:
                    self.hooks_cache[name][h] = (self.hooks.__dict__[name][h], 0,
                                                 self.hooks.__dict__[name],
                                                 self.hooks.bot)

                # Now, add extermal hooks
                level = 0
                while level == 0 or lvl_exist:
                    lvl_exist = False
                    for ext in self.network:
                        if len(self.network[ext].hooks) > level:
                            lvl_exist = True
                            for h in self.network[ext].hooks[level].__dict__[name]:
                                if h not in self.hooks_cache[name]:
                                    self.hooks_cache[name][h] = (self.network[ext].hooks[level].__dict__[name][h], level + 1, self.network[ext].hooks[level].__dict__[name], self.network[ext].hooks[level].bot)
                    level += 1

            else:
                raise Exception(name + " hook type unrecognized")

        return self.hooks_cache[name]

# Treatment

    def check_rest_times(self, store, hook):
        """Remove from store the hook if it has been executed given time"""
        if hook.times == 0:
            if isinstance(store, dict):
                store[hook.name].remove(hook)
                if len(store) == 0:
                    del store[hook.name]
            elif isinstance(store, list):
                store.remove(hook)

    def treat_pre(self, msg, srv):
        """Treat a message before all other treatment"""
        for h, lvl, store, bot in self.create_cache("all_pre"):
            if h.is_matching(None, server=srv):
                h.run(msg, self.create_cache)
                self.check_rest_times(store, h)


    def treat_post(self, res):
        """Treat a message before send"""
        for h, lvl, store, bot in self.create_cache("all_post"):
            if h.is_matching(None, channel=res.channel, server=res.server):
                c = h.run(res)
                self.check_rest_times(store, h)
                if not c:
                    return False
        return True


    def treat_irc(self, msg, srv):
        """Treat all incoming IRC commands"""
        treated = list()

        irc_hooks = self.create_cache("irc_hook")
        if msg.cmd in irc_hooks:
            (hks, lvl, store, bot) = irc_hooks[msg.cmd]
            for h in hks:
                if h.is_matching(msg.cmd, server=srv):
                    res = h.run(msg, srv, msg.cmd)
                    if res is not None and res != False:
                        treated.append(res)
                    self.check_rest_times(store, h)

        return treated


    def treat_prvmsg_ask(self, msg, srv):
        # Treat ping
        if re.match("^ *(m[' ]?entends?[ -]+tu|h?ear me|do you copy|ping)",
                    msg.content, re.I) is not None:
            return response.Response(msg.sender, message="pong",
                                     channel=msg.channel, nick=msg.nick)

        # Ask hooks
        else:
            return self.treat_ask(msg, srv)

    def treat_prvmsg(self, msg, srv):
        # First, treat CTCP
        if msg.ctcp:
            if msg.cmds[0] in self.ctcp_capabilities:
                return self.ctcp_capabilities[msg.cmds[0]](srv, msg)
            else:
                return _ctcp_response(msg.sender, "ERRMSG Unknown or unimplemented CTCP request")

        # Treat all messages starting with 'nemubot:' as distinct commands
        elif msg.content.find("%s:"%srv.nick) == 0:
            # Remove the bot name
            msg.content = msg.content[len(srv.nick)+1:].strip()

            return self.treat_prvmsg_ask(msg, srv)

        # Owner commands
        elif msg.content[0] == '`' and msg.nick == srv.owner:
            #TODO: owner commands
            pass

        elif msg.content[0] == '!' and len(msg.content) > 1:
            # Remove the !
            msg.cmds[0] = msg.cmds[0][1:]

            if msg.cmds[0] == "help":
                return _help_msg(msg.sender, self.modules, msg.cmds)

            elif msg.cmds[0] == "more":
                if msg.channel == srv.nick:
                    if msg.sender in srv.moremessages:
                        return srv.moremessages[msg.sender]
                else:
                    if msg.channel in srv.moremessages:
                        return srv.moremessages[msg.channel]

            elif msg.cmds[0] == "dcc":
                print("dcctest for", msg.sender)
                srv.send_dcc("Hello %s!" % msg.nick, msg.sender)
            elif msg.cmds[0] == "pvdcctest":
                print("dcctest")
                return Response(msg.sender, message="Test DCC")
            elif msg.cmds[0] == "dccsendtest":
                print("dccsendtest")
                conn = DCC(srv, msg.sender)
                conn.send_file("bot_sample.xml")

            else:
                return self.treat_cmd(msg, srv)

        else:
            res = self.treat_answer(msg, srv)
            # Assume the message starts with nemubot:
            if (res is None or len(res) <= 0) and msg.private:
                return self.treat_prvmsg_ask(msg, srv)
            return res


    def treat_cmd(self, msg, srv):
        """Treat a command message"""
        treated = list()

        # First, treat simple hook
        cmd_hook = self.create_cache("cmd_hook")
        if msg.cmds[0] in cmd_hook:
            (hks, lvl, store, bot) = cmd_hook[msg.cmds[0]]
            for h in hks:
                if h.is_matching(msg.cmds[0], channel=msg.channel, server=srv) and (msg.private or lvl == 0 or bot.nick not in srv.channels[msg.channel].people):
                    res = h.run(msg, strcmp=msg.cmds[0])
                    if res is not None and res != False:
                        treated.append(res)
                    self.check_rest_times(store, h)

        # Then, treat regexp based hook
        cmd_rgxp = self.create_cache("cmd_rgxp")
        for hook, lvl, store, bot in cmd_rgxp:
            if hook.is_matching(msg.cmds[0], msg.channel, server=srv) and (msg.private or lvl == 0 or bot.nick not in srv.channels[msg.channel].people):
                res = hook.run(msg)
                if res is not None and res != False:
                    treated.append(res)
                self.check_rest_times(store, hook)

        # Finally, treat default hooks if not catched before
        cmd_default = self.create_cache("cmd_default")
        for hook, lvl, store, bot in cmd_default:
            if treated:
                break
            res = hook.run(msg)
            if res is not None and res != False:
                treated.append(res)
            self.check_rest_times(store, hook)

        return treated

    def treat_ask(self, msg, srv):
        """Treat an ask message"""
        treated = list()

        # First, treat simple hook
        ask_hook = self.create_cache("ask_hook")
        if msg.content in ask_hook:
            hks, lvl, store, bot = ask_hook[msg.content]
            for h in hks:
                if h.is_matching(msg.content, channel=msg.channel, server=srv) and (msg.private or lvl == 0 or bot.nick not in srv.channels[msg.channel].people):
                    res = h.run(msg, strcmp=msg.content)
                    if res is not None and res != False:
                        treated.append(res)
                    self.check_rest_times(store, h)

        # Then, treat regexp based hook
        ask_rgxp = self.create_cache("ask_rgxp")
        for hook, lvl, store, bot in ask_rgxp:
            if hook.is_matching(msg.content, channel=msg.channel, server=srv) and (msg.private or lvl == 0 or bot.nick not in srv.channels[msg.channel].people):
                res = hook.run(msg, strcmp=msg.content)
                if res is not None and res != False:
                    treated.append(res)
                self.check_rest_times(store, hook)

        # Finally, treat default hooks if not catched before
        ask_default = self.create_cache("ask_default")
        for hook, lvl, store, bot in ask_default:
            if treated:
                break
            res = hook.run(msg)
            if res is not None and res != False:
                treated.append(res)
            self.check_rest_times(store, hook)

        return treated

    def treat_answer(self, msg, srv):
        """Treat a normal message"""
        treated = list()

        # First, treat simple hook
        msg_hook = self.create_cache("msg_hook")
        if msg.content in msg_hook:
            hks, lvl, store, bot = msg_hook[msg.content]
            for h in hks:
                if h.is_matching(msg.content, channel=msg.channel, server=srv) and (msg.private or lvl == 0 or bot.nick not in srv.channels[msg.channel].people):
                    res = h.run(msg, strcmp=msg.content)
                    if res is not None and res != False:
                        treated.append(res)
                    self.check_rest_times(store, h)

        # Then, treat regexp based hook
        msg_rgxp = self.create_cache("msg_rgxp")
        for hook, lvl, store, bot in msg_rgxp:
            if hook.is_matching(msg.content, channel=msg.channel, server=srv) and (msg.private or lvl == 0 or bot.nick not in srv.channels[msg.channel].people):
                res = hook.run(msg, strcmp=msg.content)
                if res is not None and res != False:
                    treated.append(res)
                self.check_rest_times(store, hook)

        # Finally, treat default hooks if not catched before
        msg_default = self.create_cache("msg_default")
        for hook, lvl, store, bot in msg_default:
            if len(treated) > 0:
                break
            res = hook.run(msg)
            if res is not None and res != False:
                treated.append(res)
            self.check_rest_times(store, hook)

        return treated

def _ctcp_response(sndr, msg):
    return response.Response(sndr, msg, ctcp=True)


def _help_msg(sndr, modules, cmd):
    """Parse and response to help messages"""
    res = response.Response(sndr)
    if len(cmd) > 1:
        if cmd[1] in modules:
            if len(cmd) > 2:
                if hasattr(modules[cmd[1]], "HELP_cmd"):
                    res.append_message(modules[cmd[1]].HELP_cmd(cmd[2]))
                else:
                    res.append_message("No help for command %s in module %s" % (cmd[2], cmd[1]))
            elif hasattr(modules[cmd[1]], "help_full"):
                res.append_message(modules[cmd[1]].help_full())
            else:
                res.append_message("No help for module %s" % cmd[1])
        else:
            res.append_message("No module named %s" % cmd[1])
    else:
        res.append_message("Pour me demander quelque chose, commencez "
                           "votre message par mon nom ; je réagis "
                           "également à certaine commandes commençant par"
                           " !.  Pour plus d'informations, envoyez le "
                           "message \"!more\".")
        res.append_message("Mon code source est libre, publié sous "
                           "licence AGPL (http://www.gnu.org/licenses/). "
                           "Vous pouvez le consulter, le dupliquer, "
                           "envoyer des rapports de bogues ou bien "
                           "contribuer au projet sur GitHub : "
                           "http://github.com/nemunaire/nemubot/")
        res.append_message(title="Pour plus de détails sur un module, "
                           "envoyez \"!help nomdumodule\". Voici la liste"
                           " de tous les modules disponibles localement",
                           message=["\x03\x02%s\x03\x02 (%s)" % (im, modules[im].help_tiny ()) for im in modules if hasattr(modules[im], "help_tiny")])
    return res

def hotswap(bak):
    return Bot(bak.servers, bak.modules, bak.modules_path)

def reload():
    import imp

    import channel
    imp.reload(channel)

    import consumer
    imp.reload(consumer)

    import DCC
    imp.reload(DCC)

    import event
    imp.reload(event)

    import hooks
    imp.reload(hooks)

    import importer
    imp.reload(importer)

    import message
    imp.reload(message)

    import prompt.builtins
    imp.reload(prompt.builtins)

    import server
    imp.reload(server)

    import xmlparser
    imp.reload(xmlparser)
    import xmlparser.node
    imp.reload(xmlparser.node)
