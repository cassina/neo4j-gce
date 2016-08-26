#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Save graph.db in GCS (This should be backed up every day)
# Save dir with neo4j.tar, start.py, requirements.txt
# def configure_backup(self, gcs):
# if check_alone configure this instance for backup
# create cron tab for backing up every 24
# graph = gcs.objects().get(bucket="backup", object="graph.db").execute()
# os.system("{s}  -host 0.0.0.0 -to {r}".format(s=backup_script, r=backup_path))
# google_metadata_script_runner --script-type startup
# NEO4J_URL="http://neo4j:sandbox@130.211.22.109:8080/db/data"
import os
import json
import requests

from subprocess import check_output
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery


class Neo4jClusterService:
    project = "fleet-passkey-767"
    zone = "us-central1-f"
    group = "neo4j-cluster"
    n4j_path = "/neo4j"
    n4j_home_path = n4j_path + "/neo4j-enterprise-3.0.3"
    tmp_path = n4j_path + "/temp.conf"
    conf_path = n4j_home_path + "/conf/neo4j.conf"
    backup_script = "/neo4j-enterprise-3.0.3/bin/neo4j-backup"
    backup_path = n4j_path + '/backup/graph.db'
    id_url = "http://metadata.google.internal/computeMetadata/v1/instance/id"
    ip_url = "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip"
    # id_ulr = "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip"

    ha_dbms_connector_http = "#dbms.connector.http.address=0.0.0.0:7474"
    ha_server_id = "#ha.server_id="
    ha_initial_hosts = "#ha.initial_hosts=127.0.0.1:5001,127.0.0.1:5002,127.0.0.1:5003"
    ha_dbms_mode = "#dbms.mode=HA"
    ha_status_auth = "#ha_status_auth_enabled=false"
    ha_host_data = "#ha.host.data=127.0.0.1:6001"
    ha_host_coord = "#ha.host.coordination=127.0.0.1:5001"

    def __init__(self):
        self.msg(s="New Neo4j Service Initialization")
        i_id, ips, server_ip = self.get_parse_data()
        self.msg(s="Got parsed data {i_id} {ips}".format(i_id=i_id, ips=ips))
        self.update_neo4j_conf(i_id=i_id, ips=ips, server_ip=server_ip)

    @classmethod
    def msg(cls, s):
        print("[[ {s} ]]".format(s=s))

    @classmethod
    def uncomment_line(cls, s):
        return s.strip('#')

    @classmethod
    def get_credentials(cls):
        credentials = GoogleCredentials.get_application_default()
        return credentials

    def write_neo4j_conf(self, replace_dict):
        with open(self.conf_path, "r") as old:
            with open(self.tmp_path, "w") as new_file:
                for line in old:
                    for key in replace_dict.keys():
                        if key in line:
                            line = line.replace(key, replace_dict[key])
                    new_file.write(line)
            new_file.close()
        old.close()

    def delete_tmp(self):
        deleted = os.system('mv {s} {r}'.format(s=self.tmp_path, r=self.conf_path))

    def start_neo4j(self):
        self.msg(s="Starting :7474")
        n4j_start = check_output([self.n4j_home_path + "/bin/neo4j", 'start'])
        self.msg(s=n4j_start)

    def create_gc_services(self):
        credentials = self.get_credentials()
        gce = discovery.build("compute", "v1", credentials=credentials)
        return gce

    def get_instance_info(self):
        headers = {"Metadata-Flavor": "Google"}
        server_id = requests.get(self.id_url, headers=headers)
        server_ip = requests.get(self.ip_url, headers=headers)

        return str(server_id.text[0:6]), str(server_ip)

    def get_running_vms(self, compute):
        body = {"instanceState": "RUNNING"}
        response = compute.instanceGroups().listInstances(
            project=self.project, zone=self.zone, instanceGroup=self.group, body=body
        ).execute()
        items = [item["instance"].split("/instances/")[1] + ":5001" for item in response["items"]]
        result = ",".join(items)
        # TODO Neo4j manual specifies initial hosts should be the same in every instance.
        # Comment line above and uncomment following line for master initialization
        # result = "127.0.0.1:5001"
        # result = "10.128.0.2:5001,10.128.0.4:5001,10.128.0.6:5001,10.128.0.8:5001,10.128.0.10:5001," \
        #          "10.128.0.3:5001,10.128.0.5:5001,10.128.0.7:5001,10.128.0.9:5001,10.128.0.11:5001"

        return result

    def get_parse_data(self):
        i_id, server_ip = self.get_instance_info()
        gce = self.create_gc_services()
        ips = self.get_running_vms(compute=gce)

        return i_id, ips, server_ip

    def update_neo4j_conf(self, i_id, ips, server_ip):

        self.msg(s="Updating neo4j.conf")

        server_id = "ha.server_id={instance_id}".format(instance_id=i_id)
        initial_hosts = "ha.initial_hosts={hosts}".format(hosts=ips)
        host_data = server_ip + ":6001"
        host_coord = server_ip + ":5001"

        replace_data = {
            self.ha_server_id: server_id,
            self.ha_initial_hosts: initial_hosts,
            self.ha_dbms_connector_http: self.uncomment_line(s=self.ha_dbms_connector_http),
            self.ha_dbms_mode: self.uncomment_line(s=self.ha_dbms_mode),
            self.ha_status_auth: self.uncomment_line(s=self.ha_status_auth),
            self.ha_host_data: host_data,
            self.ha_host_coord: host_coord
        }

        self.write_neo4j_conf(replace_dict=replace_data)
        self.msg(s="Updated neo4j.conf")

        self.delete_tmp()
        self.msg(s="Deleted temp.conf")

        self.start_neo4j_service()

    def start_neo4j_service(self):
        self.start_neo4j()


if __name__ == "__main__":
    new_instance = Neo4jClusterService()
