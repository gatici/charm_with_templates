#!/usr/bin/env python3
##
# Copyright 2020 Canonical Ltd.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
##
from utils import *
import logging
from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState
from ops.model import MaintenanceStatus, ActiveStatus

logger = logging.getLogger(__name__)


class VnfConf(CharmBase):
    _stored = StoredState()

    def __init__(self, framework, key):
        super().__init__(framework, key)
        # Listen to charm events
        subprocess.call(["sudo", "python3", *sys.argv])
        self._stored.set_default(
            installed=False,
            configured=False,
            started=False,
            nrfipc=None,
            vnfipm=None,
            vnfipc=None,
            host_name=None,
            vnf_osm_mgmtip=None,
            dbname="",
            dbpas="",
            dbport="",
            dbip="",
            dbuser="",
            SOURCE="./templates/settings.json",
            TARGET="/settings.json",
        )

        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.update_status, self._on_update_status)

        # Listen to the touch action event
        self.framework.observe(
            self.on.interface_relation_changed, self.on_interface_relation_changed
        )
        self.framework.observe(self.on.restartsvc_action, self.on_restartsvc_action)
        self.framework.observe(self.on.startsvc_action, self.on_startsvc_action)
        self.framework.observe(self.on.stopsvc_action, self.on_stopsvc_action)

    def _on_start(self):
        """Called when the charm is being started"""
        self.model.unit.status = ActiveStatus()

    def _on_update_status(self):
        self.unit.status = ActiveStatus()

    def _get_current_status(self):
        status_type = ActiveStatus
        status_msg = ""
        if self._stored.installed:
            status_msg = "Installed"
        if self._stored.installed and self._stored.configured:
            status_msg = "Configured"
        if self._stored.installed and self._stored.configured and self._stored.started:
            status_msg = "Ready"
        return status_type(status_msg)

    def on_interface_relation_changed(self, event):
        if not self._stored.vnfipm:
            self._stored.vnfipm = get_interface_ip("ens4")
        if not self._stored.vnfipc:
            self._stored.vnfipc = get_interface_ip("ens5")

        try:
            self._stored.nrfipc = event.relation.data[event.unit].get("nrfipc")
            if self._stored.nrfipc:
                logger.critical(
                    "RELATION DATA: {}".format(dict(event.relation.data[event.unit]))
                )
                self.model.unit.status = ActiveStatus(
                    "Parameter received: {}".format(self._stored.nrfipc)
                )
                service_restart(["vnf.service"])
                self._stored.started = True
                self.unit.status = self._get_current_status()
            logger.critical("Operation {} done".format(self.unit.status))
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )

    def on_install(self):
        self._stored.host_name = get_command_output("hostname")
        self._stored.vnf_osm_mgmtip = get_interface_ip("ens3")
        self.unit.status = MaintenanceStatus("Configuring network interfaces")

        try:
            append_line_tofile(
                self._stored.vnf_osm_mgmtip,
                self._stored.host_name,
                filename="/etc/hosts",
            )
            append_tofile(
                "auto ens4",
                "iface ens4 inet dhcp",
                "auto ens5",
                "iface ens5 inet dhcp",
                "auto ens6",
                "iface ens6 inet dhcp",
                filename="/etc/network/interfaces.d/50-cloud-init.cfg",
            )
            shell("ifup ens4")
            shell("ifup ens5")
            shell("ifup ens6")
            logger.critical("Operation {} done".format(self.unit.status))
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )

        self.unit.status = MaintenanceStatus("Restarting services")
        try:
            service_restart(["vmf.service"])
            logger.critical("Operation {} done".format(self.unit.status))
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )

    def on_config_changed(self):
        self._stored.vnfipm = get_interface_ip("ens4")
        self._stored.vnfipc = get_interface_ip("ens5")
        self.unit.status = MaintenanceStatus("Setting up directories")
        try:
            change_directory_permissions(r"/opt/vnf/", 0o777)
            extract_file(r"/bundle.tar.gz", r"/home/ubuntu/")
            logger.critical("Operation {} done".format(self.unit.status))
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )

        self.unit.status = MaintenanceStatus("Rendering temlates")
        try:
            copy_files(
                {"create2": "./templates/create2.js"},
                {"create2": "/home/ubuntu/create2.js"},
                0o777,
            )
            render_template(
                self._stored.SOURCE,
                self._stored.TARGET,
                {
                    "tdbip": self._stored.dbip,
                    "tdbport": self._stored.dbport,
                    "tdbname": self._stored.dbname,
                    "tdbuser": self._stored.dbuser,
                    "tdbpas": self._stored.dbpas,
                },
                0o777,
            )
            logger.critical("Operation {} done".format(self.unit.status))
            self._stored.configured = True
            self.unit.status = self._get_current_status()
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )

    def on_restartsvc_action(self):
        self.unit.status = MaintenanceStatus("Restarting Services")
        try:
            service_restart(["vnf.service"])
            logger.critical("Operation {} done".format(self.unit.status))
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )

    def on_startsvc_action(self):
        self.unit.status = MaintenanceStatus("Restarting Services")
        try:
            service_start(["vnf.service"])
            logger.critical("Operation {} done".format(self.unit.status))
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )

    def on_stopsvc_action(self):
        self.unit.status = MaintenanceStatus("Restarting Services")
        try:
            service_stop(["vnf.service"])
            logger.critical("Operation {} done".format(self.unit.status))
        except Exception as e:
            logger.error(
                "Operation failed: {} with error {}".format(self.unit.status, e)
            )


if __name__ == "__main__":
    main(VnfConf)
