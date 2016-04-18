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

import nemubot.message as message
from nemubot.message.printer.socket import Socket as SocketPrinter
from nemubot.server.abstract import AbstractServer


class SocketServer(AbstractServer):

    """Concrete implementation of a socket connexion (can be wrapped with TLS)"""

    def __init__(self, sock_location=None, host=None, port=None, ssl=False, socket=None, id=None):
        if id is not None:
            self.id = id
        super().__init__()
        if sock_location is not None:
            self.filename = sock_location
        elif host is not None:
            self.host = host
            self.port = int(port)
        self.ssl = ssl

        self.socket = socket
        self.readbuffer = b''
        self.printer  = SocketPrinter


    def fileno(self):
        return self.socket.fileno() if self.socket else None


    @property
    def closed(self):
        """Indicator of the connection aliveness"""
        return self.socket is None


    # Open/close

    def open(self):
        import socket

        if not self.closed:
            return True

        try:
            if hasattr(self, "filename"):
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.connect(self.filename)
                self.logger.info("Connected to %s", self.filename)
            else:
                self.socket = socket.create_connection((self.host, self.port))
                self.logger.info("Connected to %s:%d", self.host, self.port)
        except:
            self.socket = None
            if hasattr(self, "filename"):
                self.logger.exception("Unable to connect to %s",
                                      self.filename)
            else:
                self.logger.exception("Unable to connect to %s:%d",
                                      self.host, self.port)
            return False

        # Wrap the socket for SSL
        if self.ssl:
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.socket = ctx.wrap_socket(self.socket)

        return super().open()


    def close(self):
        import socket

        from nemubot.server import _lock
        _lock.release()
        self._sending_queue.join()
        _lock.acquire()
        if not self.closed:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except socket.error:
                pass

            self.socket = None

        return super().close()


    # Write

    def _write(self, cnt):
        if self.closed:
            return

        self.socket.sendall(cnt)


    def format(self, txt):
        if isinstance(txt, bytes):
            return txt + b'\r\n'
        else:
            return txt.encode() + b'\r\n'


    # Read

    def read(self):
        if self.closed:
            return []

        raw = self.socket.recv(1024)
        temp = (self.readbuffer + raw).split(b'\r\n')
        self.readbuffer = temp.pop()

        for line in temp:
            yield line


    def parse(self, line):
        import shlex

        line = line.strip().decode()
        try:
            args = shlex.split(line)
        except ValueError:
            args = line.split(' ')

        yield message.Command(cmd=args[0], args=args[1:], server=self.id, to=["you"], frm="you")


class SocketListener(AbstractServer):

    def __init__(self, new_server_cb, id, sock_location=None, host=None, port=None, ssl=None):
        self.id = id
        super().__init__()
        self.new_server_cb = new_server_cb
        self.sock_location = sock_location
        self.host = host
        self.port = port
        self.ssl = ssl
        self.nb_son = 0


    def fileno(self):
        return self.socket.fileno() if self.socket else None


    @property
    def closed(self):
        """Indicator of the connection aliveness"""
        return self.socket is None


    def open(self):
        import os
        import socket

        if self.sock_location is not None:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                os.remove(self.sock_location)
            except FileNotFoundError:
                pass
            self.socket.bind(self.sock_location)
        elif self.host is not None and self.port is not None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind((self.host, self.port))
        self.socket.listen(5)

        return super().open()


    def close(self):
        import os
        import socket

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            if self.sock_location is not None:
                os.remove(self.sock_location)
        except socket.error:
            pass

        return super().close()


    # Read

    def read(self):
        if self.closed:
            return []

        conn, addr = self.socket.accept()
        self.nb_son += 1
        ss = SocketServer(id=self.id + "#" + str(self.nb_son), socket=conn)
        self.new_server_cb(ss)

        return []
