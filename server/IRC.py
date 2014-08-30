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

import server
from server.socket import SocketServer

class IRCServer(SocketServer):

    def __init__(self, node, nick, owner, realname):
        SocketServer.__init__(self,
                              node["host"],
                              node["port"],
                              node["password"],
                              node.hasAttribute("ssl") and node["ssl"].lower() == "true")

        self.nick = nick
        self.owner = owner
        self.realname = realname
        self.id = "TODO"

    def _open(self):
        if SocketServer._open(self):
            if self.password is not None:
                self.write("PASS :" + self.password)
            self.write("NICK :" + self.nick)
            self.write("USER %s %s bla :%s" % (self.nick, self.host, self.realname))
            return True
        return False

    def _close(self):
        self.write("QUIT")
        SocketServer._close(self)
