#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Save graph.db in GCS (This should be backed up every day)
# Save dir with neo4j.tar, start.py, requirements.txt
import os
import json
import requests

from subprocess import check_output
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery

PROJECT = "novelistik-sb"
ZONE = "us-central1-f"
GROUP = "neo4j-cluster"

N4J_PATH = "/neo4j"
N4J_HOME_PATH = N4J_PATH + "neo4j-enterprise-3.0.3"
TMP_PATH = N4J_PATH + "temp.conf"
CONF_PATH = N4J_HOME_PATH + "/conf/neo4j.conf"
BACKUP_SCRIPT = "/neo4j-enterprise-3.0.3/bin/neo4j-backup"
BACKUP_PATH = N4J_PATH + '/backup/graph.db'

ID_URL = "http://metadata.google.internal/computeMetadata/v1/instance/id"

def __write_neo4j_conf(replace_dict):
	with open(CONF_PATH, "r") as old:
		with open(TMP_PATH, "w") as new_file:
			for line in old:
				for key in replace_dict.keys():
					if key in line:
						line = line.replace(key, replace_dict[key])
				new_file.write(line)
		new_file.close()
	old.close()

def __delete_tmp():
	deleted = os.system('mv {s} {r}'.format(s=TMP_PATH, r=CONF_PATH))

def __start_neo4j():
	n4j_start = check_output([N4J_HOME_PATH + "/bin/neo4j", 'start'])

def __check_graph():
	# if check_alone
	# get graph.db from GCS
	pass

def __configure_backup(gcs):
	# if check_alone configure this instance for backup
	# create cron tab for backing up every 24
	graph = gcs.objects().get(bucket="backup", object="graph.db").execute()
	os.system("{s}  -host 0.0.0.0 -to {r}".format(s=BACKUP_SCRIPT, r=BACKUP_PATH))


def __check_alone():
	# if there are no other instances in cluster 
	# return True
	pass

def get_credentials():
	credentials = GoogleCredentials.get_application_default()
	return credentials

def create_gc_services():
	credentials = get_credentials()
	gce = discovery.build("compute", "v1", credentials=credentials)
	gcs = discovery.build("storage", "v1", credentials=credentials)
	return gce, gcs

def get_instance_id():
	headers = {"Metadata-Flavor": "Google"}
	result = requests.get(ID_URL, headers=headers)
	return result

def get_running_vms(compute, group=GROUP, zone=ZONE, project=PROJECT):
	is_master = False
	body = {"instanceState": "RUNNING"}
	response = compute.instanceGroups().listInstances(project=project, zone=zone, instanceGroup=group, body=body).execute()
	items = [item["instance"].split("/instances/")[1] + ":5001" for item in response["items"]]
	result = ",".join(items)
	if len(response["items"]) <= 1:
		is_master = True

	return result, is_master
	

def get_parse_data():
	i_id = get_instance_id()
	gce, gcs  = create_gc_services()
	ips, is_master = get_running_vms(compute=compute)
	return i_id, ips, is_master, gcs

def uncomment_line(s):
	return s.strip('#')[1]

def update_neo4j_conf(i_id, ips, is_master, gcs):
	ha_server_id = "#ha.server_id="
	ha_initial_hosts = "#ha.initial_hosts=127.0.0.1:5001,127.0.0.1:5002,127.0.0.1:5003"
	ha_dbms_http = "#dbms.connector.http.address=0.0.0.0:7474"
	ha_dbms_mode = "#dbms.mode=HA"
	ha_host_coord = "#ha.host.coordination=127.0.0.1:5001"
	ha_host_data = "#ha.host.data=127.0.0.1:6001"
	ha_dbms_backup = "#dbms.backup.enabled=true"
	
	server_id = "ha.server_id={instance_id}".format(instance_id=i_id)
	initial_hosts = "ha.initial_hosts={hosts}".format(hosts=ips)

	replace_data = {
		ha_server_id: server_id,
		ha_initial_hosts: initial_hosts,
		ha_dbms_http: uncomment_line(s=ha_dbms_http),
		ha_dbms_mode: uncomment_line(s=ha_dbms_mode),
		ha_host_coord: uncomment_line(s=ha_host_coord),
		ha_host_data: uncomment_line(s=ha_host_data)
	}

	if is_master:
		replace_data[ha_dbms_backup] = uncomment_line(s=ha_dbms_backup)
		__configure_backup(gcs)

	__write_neo4j_conf(replace_dict=replace_data)

	start_neo4j_service()
	

def start_neo4j_service():
	__delete_tmp()
	__start_neo4j()

def init():
	sys_update = os.system("apt-get update")
	i_id, ips, is_master, gcs = get_parse_data()
	update_neo4j_conf(i_id=i_id, ips=ips, is_master=is_master)

if __name__ == "__main__":
	init()




