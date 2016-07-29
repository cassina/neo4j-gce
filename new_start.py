#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Save graph.db in GCS (This should be backed up every day)
# Save dir with neo4j.tar, start.py, requirements.txt
# def configure_backup(self, gcs):
# if check_alone configure this instance for backup
# create cron tab for backing up every 24
# graph = gcs.objects().get(bucket="backup", object="graph.db").execute()
# os.system("{s}  -host 0.0.0.0 -to {r}".format(s=backup_script, r=backup_path))
import os
import json
import requests

from subprocess import check_output
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery


class Neo4jClusterService:
    project = "novelistik-sb"
    zone = "us-central1-f"
    group = "neo4j-cluster"
    n4j_path = "/neo4j"
    n4j_home_path = n4j_path + "neo4j-enterprise-3.0.3"
    tmp_path = n4j_path + "temp.conf"
    conf_path = n4j_home_path + "/conf/neo4j.conf"
    backup_script = "/neo4j-enterprise-3.0.3/bin/neo4j-backup"
    backup_path = n4j_path + '/backup/graph.db'
    id_url = "http://metadata.google.internal/computeMetadata/v1/instance/id"

    ha_server_id = "#ha.server_id="
    ha_initial_hosts = "#ha.initial_hosts=127.0.0.1:5001,127.0.0.1:5002,127.0.0.1:5003"
    ha_dbms_http = "#dbms.connector.http.address=0.0.0.0:7474"
    ha_dbms_mode = "#dbms.mode=HA"
    ha_host_coord = "#ha.host.coordination=127.0.0.1:5001"
    ha_host_data = "#ha.host.data=127.0.0.1:6001"
    ha_dbms_backup = "#dbms.backup.enabled=true"

    def __init__(self):
        i_id, ips = self.get_parse_data()
        self.update_neo4j_conf(i_id=i_id, ips=ips)

    @classmethod
    def uncomment_line(cls, s):
        return s.strip('#')[1]

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
        n4j_start = check_output([self.n4j_home_path + "/bin/neo4j", 'start'])

    def create_gc_services(self):
        credentials = self.get_credentials()
        gce = discovery.build("compute", "v1", credentials=credentials)
        return gce

    def get_instance_id(self):
        headers = {"Metadata-Flavor": "Google"}
        result = requests.get(self.id_url, headers=headers)
        return result

    def get_running_vms(self, compute):
        body = {"instanceState": "RUNNING"}
        response = compute.instanceGroups().listInstances(project=self.project, zone=self.zone, instanceGroup=self.group,
                                                          body=body).execute()
        items = [item["instance"].split("/instances/")[1] + ":5001" for item in response["items"]]
        result = ",".join(items)

        return result

    def get_parse_data(self):
        i_id = self.get_instance_id()
        gce = self.create_gc_services()
        ips = self.get_running_vms(compute=gce)
        return i_id, ips

    def update_neo4j_conf(self, i_id, ips):

        server_id = "ha.server_id={instance_id}".format(instance_id=i_id)
        initial_hosts = "ha.initial_hosts={hosts}".format(hosts=ips)

        replace_data = {
            self.ha_server_id: server_id,
            self.ha_initial_hosts: initial_hosts,
            self.ha_dbms_http: self.uncomment_line(s=self.ha_dbms_http),
            self.ha_dbms_mode: self.uncomment_line(s=self.ha_dbms_mode),
            self.ha_host_coord: self.uncomment_line(s=self.ha_host_coord),
            self.ha_host_data: self.uncomment_line(s=self.ha_host_data)
        }

        self.write_neo4j_conf(replace_dict=replace_data)

        self.start_neo4j_service()

    def start_neo4j_service(self):
        self.delete_tmp()
        self.start_neo4j()


if __name__ == "__main__":
    new_instance = Neo4jClusterService()
