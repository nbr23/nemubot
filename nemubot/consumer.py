# -*- coding: utf-8 -*-

# Nemubot is a smart and modulable IM bot.
# Copyright (C) 2012-2015  Mercier Pierre-Olivier
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

import logging
import queue
import threading

logger = logging.getLogger("nemubot.consumer")


class MessageConsumer:

    """Store a message before treating"""

    def __init__(self, srv, msg):
        self.srv = srv
        self.orig = msg


    def run(self, context):
        """Create, parse and treat the message"""

        from nemubot.bot import Bot
        assert isinstance(context, Bot)

        msgs = []

        # Parse the message
        try:
            for msg in self.srv.parse(self.orig):
                msgs.append(msg)
        except:
            logger.exception("Error occurred during the processing of the %s: "
                             "%s", type(self.msgs[0]).__name__, self.msgs[0])

        if len(msgs) <= 0:
            return

        # Qualify the message
        if not hasattr(msg, "server") or msg.server is None:
            msg.server = self.srv.id
        if hasattr(msg, "frm_owner"):
            msg.frm_owner = (not hasattr(self.srv, "owner") or self.srv.owner == msg.frm)

        # Treat the message
        for msg in msgs:
            for res in context.treater.treat_msg(msg):
                # Identify the destination
                to_server = None
                if isinstance(res, str):
                    to_server = self.srv
                elif res.server is None:
                    to_server = self.srv
                    res.server = self.srv.id
                elif isinstance(res.server, str) and res.server in context.servers:
                    to_server = context.servers[res.server]

                if to_server is None:
                    logger.error("The server defined in this response doesn't "
                                 "exist: %s", res.server)
                    continue

                # Sent the message only if treat_post authorize it
                to_server.send_response(res)


class EventConsumer:

    """Store a event before treating"""

    def __init__(self, evt, timeout=20):
        self.evt = evt
        self.timeout = timeout


    def run(self, context):
        try:
            self.evt.check()
        except:
            logger.exception("Error during event end")

        # Reappend the event in the queue if it has next iteration
        if self.evt.next is not None:
            context.add_event(self.evt, eid=self.evt.id)

        # Or remove reference of this event
        elif (hasattr(self.evt, "module_src") and
              self.evt.module_src is not None):
            self.evt.module_src.__nemubot_context__.events.remove(self.evt.id)



class Consumer(threading.Thread):

    """Dequeue and exec requested action"""

    def __init__(self, context):
        self.context = context
        self.stop = False
        threading.Thread.__init__(self)


    def run(self):
        try:
            while not self.stop:
                stm = self.context.cnsr_queue.get(True, 1)
                stm.run(self.context)
                self.context.cnsr_queue.task_done()

        except queue.Empty:
            pass
        finally:
            self.context.cnsr_thrd_size -= 2
            self.context.cnsr_thrd.remove(self)
