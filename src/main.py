#!/usr/bin/python3 -tt
# -*- coding: iso-8859-1 -*-
#    Yum Exteder (yumex) - A GUI for yum
#    Copyright (C) 2013 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys
import os.path

here = sys.path[0]
if here != '/usr/bin':
    # git checkout
    sys.path[0] = here
    print("set PYTHONPATH to %s" % here)


from yumex import YumexApplication

app = YumexApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
