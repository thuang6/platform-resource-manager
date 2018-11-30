Simple demo scenario
....................
This document describes how to run the simple scenario on a single node.

Assumptions:

- service Mesos node address: 100.64.176.13
- load generator Mesos node address: 100.64.176.21
- docker registry address: 100.64.176.13
- working directory: PRM project top level directory
- an user having root priviliges on 100.64.176.13: user_abc


#. export needed shell variables:

.. code-block:: sh

export REMOTE_USER=user_abc
export REMOTE_IP=100.64.176.13


#. kill all jobs, stop agant and clean a temporary model data:

.. code-block:: sh

    ansible-playbook -l $REMOTE_IP -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs -v
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -msystemd -a'name=owca state=stopped'
    ansible -u $REMOTE_USER -b all -i $REMOTE_IP, -a'rm -f /var/lib/owca/lc-util.csv /var/lib/owca/workload-meta.json /var/lib/owca/workload-data.csv /var/lib/owca/threshold.json'

#. run twemcache and tensorflow workloads to build model:

.. code-block:: sh

    ansible-playbook -l $REMOTE_IP -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs,twemcache_mutilate,tensorflow_benchmark_prediction,cassandra_stress--cassandra

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

    ansible-playbook -l $REMOTE_IP -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=cassandra_stress--stress

#. kill cassandra load generator (stress) and observe anomaly disappers:

.. code-block:: sh

    ansible-playbook -l $REMOTE_IP -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs -ekill_job_name=cassandra_stress--cassandra_stress--9142 -v
