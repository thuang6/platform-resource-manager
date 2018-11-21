Simple demo scenario
....................

Assumptions:

- service Mesos node address: 100.64.176.13
- load generator Mesos node address: 100.64.176.21
- docker registry address: 100.64.176.13
- working directory: PRM project top level directory

#. kill all jobs, stop agant and clean a temporary model data::

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs -v
    ansible -b all -i 100.64.176.13, -msystemd -a'name=owca state=stopped'
    ansible -b all -i 100.64.176.13, -a'rm -f /tmp/lc-util.csv /tmp/workload-meta.json /tmp/workload-data.csv /tmp/threshold.json'

#. run twemcache and tensorflow workloads to build model::

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs,twemcache_mutilate,tensorflow_benchmark_prediction,cassandra_stress--cassandra

#. reconfigure and restart OWCA+PRM to run in collect mode::

    ansible -b all -i 100.64.176.13, -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp="detect" replace="collect"'
    ansible -b all -i 100.64.176.13, -msystemd -a'name=owca state=restarted'

#. switch to detect mode::

    ansible -b all -i 100.64.176.13, -mreplace -a'path=/etc/owca/owca_config.yml after=detector regexp=collect replace=detect'
    ansible -b all -i 100.64.176.13, -msystemd -a'name=owca state=restarted'

#. run cassandra load generator as best effort workload::

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=cassandra_stress--stress

#. kill cassandra load generator (stress) and observe anomaly disappers::

    ansible-playbook -i simple_demo_scenario/inventory.yaml owca/workloads/run_workloads.yaml --tags=clean_jobs -ekill_job_name=cassandra_stress--cassandra_stress--9142 -v
