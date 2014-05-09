# -*- coding: utf-8 -*-
#    Yum Exteder (yumex) - A graphic package management tool
#    Copyright (C) 2013 -2014 Tim Lauridsen < timlau<AT>fedoraproject<DOT>org >
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


from __future__ import absolute_import

import re
import datetime
import subprocess
import logging

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gio

from yumex.misc import _, format_block
from yumex import const
import yumex.gui.views

logger = logging.getLogger('yumex.gui.widget')


class InfoProgressBar:

    def __init__(self, ui):
        self.ui = ui
        self.infobar = ui.get_object("infobar")  # infobar revealer
        frame = ui.get_object("info_frame")
        new_bg = Gdk.RGBA()
        new_bg.parse("rgb(255,255,255)")
        frame.override_background_color(Gtk.StateFlags.NORMAL, new_bg)
        self.label = ui.get_object("infobar_label")
        self.sublabel = ui.get_object("infobar_sublabel")
        self.progress = ui.get_object("infobar_progress")

    def _show_infobar(self, show=True):
        self.infobar.set_reveal_child(show)

    def show_progress(self, state):
        if state:
            self.show_label()
        else:
            self.hide()

    def hide(self):
        self.label.hide()
        self.sublabel.hide()
        self.progress.hide()
        self._show_infobar(False)
        self.progress.set_text("")
        #self.progress.set_show_text (False)

    def hide_sublabel(self):
        self.sublabel.hide()

    def show_label(self):
        self.label.show()
        self.label.set_text("")

    def show_sublabel(self):
        self.sublabel.show()
        self.sublabel.set_text("")

    def show_all(self):
        self.show_label()
        self.show_sublabel()
        self.progress.show()

    def info(self, msg):
        self._show_infobar(True)
        self.show_label()
        self.label.set_text(msg)

    def info_sub(self, msg):
        self._show_infobar(True)
        self.show_sublabel()
        self.sublabel.set_text(msg)

    def set_progress(self, frac, label=None):
        if label:
            self.progress.set_text(label)
        if frac >= 0.0 and frac <= 1.0:
            self.infobar.show()
            self.progress.show()
            self.progress.set_fraction(frac)
            # make sure that the main label is shown, else the progres
            # looks bad. this is normally happen when changlog
            # or filelist info is needed for at package
            # and it will trigger the yum daemon to download the need metadata.
            if not self.label.get_property('visible'):
                self.info(_("Getting Package metadata"))


class ArchMenu(GObject.GObject):
    '''
    Class to handle a menu to select what arch to show in package view
    '''
    __gsignals__ = {'arch-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,))}

    def __init__(self, arch_menu_widget, archs):
        GObject.GObject.__init__(self)
        self.all_archs = archs
        self.current_archs = archs
        self.arch_menu_widget = arch_menu_widget
        self.arch_menu = self._setup_archmenu()

    def _setup_archmenu(self):
        arch_menu = self.arch_menu_widget
        for arch in self.all_archs:
            cb = Gtk.CheckMenuItem()
            cb.set_label(arch)
            cb.set_active(True)
            cb.show()
            cb.connect('toggled', self.on_archmenu_clicked)
            arch_menu.add(cb)
        return arch_menu

    def on_arch_clicked(self, button, event=None):
        #print('clicked : event : %s' % event.type)
        if event:
            self.arch_menu.popup(
                None, None, None, None, event.button, event.time)
            return True

    def on_archmenu_clicked(self, widget):
        state = widget.get_active()
        label = widget.get_label()
        if state:
            self.current_archs.append(label)
        else:
            self.current_archs.remove(label)
        archs = ",".join(self.current_archs)
        self.emit("arch-changed", archs)


class PackageInfoWidget(Gtk.Box):
    __gsignals__ = {'info-changed': (GObject.SignalFlags.RUN_FIRST,
                                     None,
                                     (GObject.TYPE_STRING,))
                    }

    def __init__(self, window, url_handler):
        Gtk.Box.__init__(self)
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        # PKGINFO_FILTERS = ['desc', 'updinfo', 'changelog', 'files', 'deps']
        rb = self._get_radio_button('dialog-information-symbolic', "desc")
        vbox.add(rb)
        vbox.add(self._get_radio_button(
            'software-update-available-symbolic', "updinfo", rb))
        vbox.add(self._get_radio_button(
            'bookmark-new-symbolic', "changelog", rb))
        vbox.add(self._get_radio_button(
            'drive-multidisk-symbolic', "files", rb))
        vbox.add(self._get_radio_button('insert-object-symbolic', "deps", rb))
        vbox.set_margin_right(5)
        self.pack_start(vbox, False, False, 0)
        sw = Gtk.ScrolledWindow()
        self.view = yumex.gui.views.PackageInfoView(window, url_handler)
        sw.add(self.view)
        self.pack_start(sw, True, True, 0)

    def _get_radio_button(self, icon_name, name, group=None):
        if group:
            wid = Gtk.RadioButton.new_from_widget(group)
        else:
            wid = Gtk.RadioButton()
        icon = Gio.ThemedIcon(name=icon_name)
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU)
        wid.set_image(image)
        wid.connect('toggled', self._on_filter_changed, name)
        # we only want an image, not the black dot indicator
        wid.set_property("draw-indicator", False)
        return wid

    def _on_filter_changed(self, button, data):
        '''
        Radio Button changed handler
        Change the info in the view to match the selection
Gtk.Image()
        :param button:
        :param data:
        '''
        if button.get_active():
            logger.debug("pkginfo: %s selected" % data)
            self.emit("info-changed", data)


class PackageInfo(PackageInfoWidget):
    '''
    class for handling the Package Information view
    '''

    def __init__(self, window, base):
        PackageInfoWidget.__init__(self, window, url_handler=self._url_handler)
        self.window = window
        self.base = base
        self.current_package = None
        self.active_filter = const.PKGINFO_FILTERS[0]
        self.connect('info-changed', self.on_filter_changed)
        self.update()

    def on_filter_changed(self, widget, data):
        self.active_filter = data
        self.update()

    def set_package(self, pkg):
        '''
        Set current active package to show information about in the
        Package Info view.

        :param pkg: package to set as active package
        '''
        self.current_package = pkg
        self.update()

    def update(self):
        '''
        update the information in the Package info view
        '''
        self.view.clear()
        self.view.write("\n")
        if self.current_package:
            if self.active_filter == 'desc':
                self._show_description()
            elif self.active_filter == 'updinfo':
                self._show_updateinfo()

            elif self.active_filter == 'changelog':
                self._show_changelog()

            elif self.active_filter == 'files':
                self._show_filelist()

            elif self.active_filter == 'deps':
                self._show_requirements()
            else:
                print("Package info not found : ", self.active_filter)
        self.view.goTop()

    def _is_url(self, url):
        urls = re.findall(
            '^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|'
            '[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', url)
        if urls:
            return True
        else:
            return False

    def _url_handler(self, url):
        print('Url activated : ' + url)
        if self._is_url(url):  # just to be sure and prevent shell injection
            rc = subprocess.call("xdg-open %s" % url, shell=True)
            # failover to gtk.show_uri, if xdg-open fails or is not installed
            if rc != 0:
                Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        else:
            self.frontend.warning("%s is not an url" % url)

    def _show_description(self):
        tags = self.current_package.pkgtags
        if tags:
            self.view.write(_("Tags : %s\n ") %
                            ", ".join(tags), "changelog-header")
        url = self.current_package.URL
        self.view.write(_("Project URL : "), "changelog-header", newline=False)
        self.view.add_url(url, url, newline=True)
        self.view.write('\n')

        desc = self.current_package.description
        self.view.write(desc)
        self.base.set_working(False)

    def _show_updateinfo(self):
        self.base.set_working(True)
        updinfo = self.current_package.updateinfo
        if updinfo:
            for info in updinfo:
                self._write_update_info(info)
        else:
            self.view.write(_("No Update information is available"))
        self.base.set_working(False)

    def _write_update_info(self, upd_info):
        head = ""
        head += ("%14s " % _("Release")) + ": %(release)s\n"
        head += ("%14s " % _("Type")) + ": %(type)s\n"
        head += ("%14s " % _("Status")) + ": %(status)s\n"
        head += ("%14s " % _("Issued")) + ": %(issued)s\n"
        head = head % upd_info

        if upd_info['updated'] and upd_info['updated'] != upd_info['issued']:
            head += "    Updated : %s" % upd_info['updated']

        self.view.write(head)
        head = ""

        # Add our bugzilla references
        if upd_info['references']:
            bzs = [r for r in upd_info['references']
                   if r and r['type'] == 'bugzilla']
            if len(bzs):
                header = "Bugzilla"
                for bz in bzs:
                    if 'title' in bz and bz['title']:
                        bug_msg = ' - %s' % bz['title']
                    else:
                        bug_msg = ''
                    self.view.write("%14s : " % header, newline=False)
                    self.view.add_url(bz['id'], const.BUGZILLA_URL + bz['id'])
                    self.view.write(bug_msg)
                    header = " "

        # Add our CVE references
        if upd_info['references']:
            cves = [r for r in upd_info['references']
                    if r and r['type'] == 'cve']
            if len(cves):
                cvelist = ""
                header = "CVE"
                for cve in cves:
                    cvelist += "%14s : %s\n" % (header, cve['id'])
                    header = " "
                head += cvelist[:-1].rstrip() + '\n\n'

        if upd_info['description'] is not None:
            desc = upd_info['description']
            head += "\n%14s : %s\n" % (_("Description"),
                                       format_block(desc, 17))

        head += "\n"
        self.view.write(head)

    def _show_changelog(self):
        self.base.set_working(True)
        changelog = self.current_package.changelog
        if changelog:
            i = 0
            for (c_date, c_ver, msg) in changelog:
                i += 1
                self.view.write(
                    "* %s %s" %
                    (datetime.date.fromtimestamp(c_date).isoformat(), c_ver),
                    "changelog-header")
                for line in msg.split('\n'):
                    self.view.write("%s" % line, "changelog")
                self.view.write('\n')
                if i == 5:  # only show the last 5 entries
                    break
        else:
            self.view.write(_("No Changelog information is available"))

        self.base.set_working(False)

    def _show_filelist(self):
        self.base.set_working(True)
        filelist = self.current_package.filelist
        if filelist:
            for fname in sorted(filelist):
                self.view.write(fname)
        else:
            self.view.write(_("No Filelist information is available"))
        self.base.set_working(False)

    def _show_requirements(self):
        self.view.write("Requirements for " + str(self.current_package))


def ask_for_gpg_import(window, values):
    (pkg_id, userid, hexkeyid, keyurl, timestamp) = values
    pkg_name = pkg_id.split(',')[0]
    msg = (_(' Do you want to import this GPG Key\n'
             ' Needed to verify the %s package\n\n'
             ' key        : 0x%s:\n'
             ' Userid     : "%s"\n'
             ' From       : %s') %
          (pkg_name, hexkeyid, userid,
           keyurl.replace("file://", "")))

    dialog = Gtk.MessageDialog(
        window, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, msg)
    rc = dialog.run()
    dialog.destroy()
    return rc == Gtk.ResponseType.YES
