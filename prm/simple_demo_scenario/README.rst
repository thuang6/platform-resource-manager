Simple demo scenario
....................
This document describes how to run the simple scenario on a single node.

Assumptions:

- service Mesos node address: 100.64.176.13
- load generator Mesos node address: 100.64.176.21
- docker registry address: 100.64.176.13
- working directory: PRM project top level directory
- export variable $REMOTE_USER to user which should execute command on the remote
- export variable $REMOTE_IP to IP address of the remote

#. kill all jobs, stop agant and clean a temporary model data:

.. code-block:: sh

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs -v
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=stopped'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -a'rm -f /var/lib/owca/lc-util.csv /var/lib/owca/workload-meta.json /var/lib/owca/workload-data.csv /var/lib/owca/threshold.json'

#. run twemcache and tensorflow workloads to build model:

.. code-block:: sh

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs,twemcache_mutilate,tensorflow_benchmark_prediction,cassandra_stress--cassandra

#. reconfigure (set action_delay to 20seconds) and restart OWCA+PRM to run in collect mode

.. code-block:: sh

    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp="detect" replace="collect"'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -mreplace -a'path=/etc/owca/owca_config.yml regexp="action_delay: .*" replace="action_delay: 20."'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=restarted'

#. switch to detect mode:

.. code-block:: sh

    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp=collect replace=detect'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=restarted'

#. run cassandra load generator as best effort workload:

.. code-block:: sh

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=cassandra_stress--stress

#. kill cassandra load generator (stress) and observe anomaly disappers:

.. code-block:: sh

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs -ekill_job_name=cassandra_stress--cassandra_stress--9142 -v
