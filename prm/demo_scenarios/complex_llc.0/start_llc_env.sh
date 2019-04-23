#! /bin/bash

export REMOTE_USER=ssg
export REMOTE_IP=100.64.176.20
export cinventory=demo_scenarios/common/common.yaml
export playbook=owca/workloads/run_workloads.yaml

ansible-playbook -l $REMOTE_IP -i $cinventory $playbook --tags=clean_jobs -v
ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=stopped'
ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -a'rm -f /var/lib/owca/lc-util.csv /var/lib/owca/workload-meta.json /var/lib/owca/workload-data.csv /var/lib/owca/threshold.json'

ansible-playbook -l $REMOTE_IP -i demo_scenarios/complex_llc.0/inventory.yaml -i $cinventory $playbook \
  --tags=twemcache_mutilate,redis_rpc_perf,cassandra_stress--cassandra
