#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Nemubot is a modulable IRC bot, built around XML configuration files.
# Copyright (C) 2012  Mercier Pierre-Olivier
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

import sys
import os
import imp
import traceback

import bot
import prompt
from prompt.builtins import load_file
import importer

if __name__ == "__main__":
    # Create bot context
    context = bot.Bot(0, "FIXME")

    # Load the prompt
    prmpt = prompt.Prompt()

    # Register the hook for futur import
    sys.meta_path.append(importer.ModuleFinder(context, prmpt))

    #Add modules dir path
    if os.path.isdir("./modules/"):
        context.add_modules_path(
            os.path.realpath(os.path.abspath("./modules/")))

    # Parse command line arguments
    if len(sys.argv) >= 2:
        for arg in sys.argv[1:]:
            if os.path.isdir(arg):
                context.add_modules_path(arg)
            else:
                load_file(arg, context)

    print ("Nemubot v%s ready, my PID is %i!" % (context.version_txt,
                                                 os.getpid()))
    while prmpt.run(context):
        try:
            # Reload context
            imp.reload(bot)
            context = bot.hotswap(context)
            # Reload prompt
            imp.reload(prompt)
            prmpt = prompt.hotswap(prmpt)
            # Reload all other modules
            bot.reload()
            print ("\033[1;32mContext reloaded\033[0m, now in Nemubot %s" %
                   context.version_txt)
        except:
            print ("\033[1;31mUnable to reload the prompt due to errors.\033[0"
                   "m Fix them before trying to reload the prompt.")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sys.stderr.write (traceback.format_exception_only(exc_type,
                                                              exc_value)[0])

    print ("\nWaiting for other threads shuts down...")

    # Indeed, the server socket is waiting for receiving some data

    sys.exit(0)
