#! /bin/bash
virtualenv neo4j-cluster/venv --python python2.7
source neo4j-cluster/venv/bin/activate
pip install -r neo4j-cluster/requirements.txt
python neo4j-cluster/start.py
echo "--- DONE ---"