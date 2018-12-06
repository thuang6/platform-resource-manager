LLC demo scenario
....................
This document contains commands to run the scenario on a single node.

Firstly please define auxiliary variables (to shorten the notation):

.. code-block:: sh
    REMOTE_USER=sbugaj
    REMOTE_IP=100.64.176.15
    inventory=demo_scenarios/complex_llc.0/inventory.yaml
    workloads_playbook=owca/workloads/run_workloads.yaml


To put PRM into collect mode and reset state:
 
.. code-block:: sh

    # switch owca into collect mode (clean state of prm)
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp="detect" replace="collect"'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -mreplace -a'path=/etc/owca/owca_config.yml regexp="action_delay: .*" replace="action_delay: 20."'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=stopped'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -a'rm -f /var/lib/owca/lc-util.csv /var/lib/owca/workload-meta.json /var/lib/owca/workload-data.csv /var/lib/owca/threshold.json'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=restarted'

.. code-block:: sh

    # clean all jobs on the node
    ansible-playbook -l $REMOTE_IP -i $inventory $workloads_playbook --tags=clean_jobs -v

    # run needed workloads
    ansible-playbook -l $REMOTE_IP -i $inventory $workloads_playbook --tags=twemcache_mutilate,redis_rpc_perf,cassandra_stress--cassandra
    #ansible-playbook -l $REMOTE_IP -i $inventory $workloads_playbook --tags=twemcache_mutilate

    # to check status
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -a'cat /etc/owca/owca_config.yml'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -a'systemctl status owca'
    ansible -u $REMOTE_USER -b all -i 100.64.176.13, -a'ls -la /var/lib/owca/'

    # to switch to detect mode
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp=collect replace=detect'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=restarted'
    ansible-playbook -l $REMOTE_IP -i $inventory $workloads_playbook --tags=cassandra_stress--stress -vvv

    # kill cassandra load generator (stress) and observe anomaly disappers:
    ansible-playbook -l $REMOTE_IP -i $inventory $workloads_playbook --tags=clean_jobs -ekill_job_name=cassandra_stress.default--cassandra_stress--9142.0 -v
