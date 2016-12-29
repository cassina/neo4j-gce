#! /bin/bash
apt-get update
cd /neo4j
TOKEN=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/token -H "Metadata-Flavor: Google")
git clone https://github.com/cassina/neo4jgce.git
bash ./neo4j-cluster/start.sh
