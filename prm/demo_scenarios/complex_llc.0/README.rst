LLC demo scenario
....................
This document contains commands to run the scenario on a single node.

Firstly please define auxiliary variables (to shorten the notation):

.. code-block:: sh
    # variables to be exported
    REMOTE_USER=sbugaj
    REMOTE_IP=100.64.176.14
    # for ansible ad-hoc commands additional flags
    flags_adhoc="-u $REMOTE_USER -b all -i $REMOTE_IP,"
    # for ansible playbook additional flags
    flags_playbook="-l $REMOTE_IP -i complex_demo_scenario/llc_inventory.yaml owca/workloads/run_workloads.yaml"


To put PRM into collect mode and reset state:
 
.. code-block:: sh

    # switch owca into collect mode (clean state of prm)
    ansible $flags_adhoc -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp="detect" replace="collect"'
    ansible $flags_adhoc -mreplace -a'path=/etc/owca/owca_config.yml regexp="action_delay: .*" replace="action_delay: 20."'
    ansible $flags_adhoc -msystemd -a'name=owca state=stopped'
    ansible $flags_adhoc -a'rm -f /var/lib/owca/lc-util.csv /var/lib/owca/workload-meta.json /var/lib/owca/workload-data.csv /var/lib/owca/threshold.json'
    ansible $flags_adhoc -msystemd -a'name=owca state=restarted'

.. code-block:: sh

    # clean all jobs on the node
    ansible-playbook $flags_playbook --tags=clean_jobs -v

    # run needed workloads
    ansible-playbook $flags_playbook --tags=twemcache_mutilate,redis_rpc_perf,cassandra_stress--cassandra

    # to check status
    ansible $flags_adhoc -a'cat /etc/owca/owca_config.yml'
    ansible $flags_adhoc -a'systemctl status owca'
    ansible -u $REMOTE_USER -b all -i 100.64.176.13, -a'ls -la /var/lib/owca/'

    # to switch to detect mode
    ansible $flags_adhoc -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp=collect replace=detect'
    ansible $flags_adhoc -msystemd -a'name=owca state=restarted'
    ansible-playbook $flags_playbook --tags=cassandra_stress--stress -vvv

    # kill cassandra load generator (stress) and observe anomaly disappers:
    ansible-playbook $flags_playbook --tags=clean_jobs -ekill_job_name=cassandra_stress.default--cassandra_stress--9142.0 -v
