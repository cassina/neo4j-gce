#! /bin/bash
apt-get update
cd /neo4j
git clone https://github.com/cassina/neo4j-gce.git
bash ./neo4j-cluster/start.sh