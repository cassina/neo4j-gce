#! /bin/bash
virtualenv venv --python python2.7
source venv/bin/activate
pip install -r requirements.txt
python neo4j-cluster/new_start.py
echo "--- DONE ---"
