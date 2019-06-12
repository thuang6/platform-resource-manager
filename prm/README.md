# Intel® PRM plugin for WCA

This readme describes the Intel® Platform Resource Manager (Intel® PRM) plugin
for the Workload Collocation Agent (WCA).

## Description

The Intel® PRM plugin uses hardware and OS metrics to build a model and detect
contention on work node. Also it supports dynamic resource allocation on best-efforts
workloads to mitigate resource contention on work node.

For WCA details, including an installation guide, refer to [WCA](https://github.com/intel/workload-collocation-agent).

## Required WCA labels

You must pass the following labels when you schedule workloads:

* `application`
* `application_version_name`

The second label is required because multiple instances of the same application
may exist, which requires separate statistical models.

For example, two instances of `twemcache` with different allocated vCPU count
needs separate models. Therefore, the label `application_version_name` must be
different for each of the `twemcache` instances.

Also if you need to support dynamic resource allocation, following label is required
to label the task as best-efforts workload by setting label value to 'best_efforts'

 * `type`

## Build

Use the commands:

```
cd ..
git submodule update --init
cd prm
make
```

## Configuration

### Contention Detection Only
The example prm agent configuration file is `wca_detect_prm.yaml`.

```yaml
runner: !DetectionRunner
  node: !MesosNode
    mesos_agent_endpoint: "http://127.0.0.1:5051"
  action_delay: &action_delay 1.
  metrics_storage: !LogStorage
    output_filename: 'metrics/metrics.prom'
    overwrite: true
  anomalies_storage: !LogStorage
    output_filename: 'metrics/anomalies.prom'
    overwrite: true
  detector: !ContentionDetector
    action_delay: *action_delay
  # Available value: 'collect'/'detect'
  # prm collects data of mesos container and writes the data into a csv file under 'collect' mode.
  # prm will build the model based on the data collected and detect the contention under 'detect' mode.
    mode_config: 'detect'
  # if agg_period value is multiple times of action_delay, prm will aggregate metrics based on agg_period
  # or it will record metrics based on action_delay
    agg_period: 20.
    database: !ModelDatabase
        db_type: etcd    # 1) local 2)zookeeper 3)etcd
        directory: ~     # required for local
        host: "10.239.157.129:2379"     # required for zookeeper and etcd
        namespace: ~     # for zookeeper, if none, using default model_distribution
        ssl_verify: false     # for etcd, default false
        api_path: "/v3beta"     # for etcd, '/v3alpha' for 3.2.x etcd version, '/v3beta' or '/v3' for 3.3.x etcd version
        timeout: 5.0     # for etcd, default 5.0 seconds
        client_cert_path: ~    # for etcd, default None
        client_key_path: ~     # for etcd, default None
    model_pull_cycle:  # how many cycles needs to be waited after previous model pulling, default 180 cycles
  # prm will detect contention base on the rdt. This configuration must be enabled.
  rdt_enabled: True
  # key value pairs to tag the data
  extra_labels:
    env_uniq_id: "120"
    own_ip: "10.3.88.120"
```

### Contention Detection and Resource Allocation
The example prm agent configuration file is `wca_alloc_prm.yaml`.

```yaml
runner: !AllocationRunner
  node: !MesosNode
    mesos_agent_endpoint: "http://127.0.0.1:5051"
  action_delay: &action_delay 1.
  metrics_storage: !LogStorage
    output_filename: 'metrics/metrics.prom'
    overwrite: true
  anomalies_storage: !LogStorage
    output_filename: 'metrics/anomalies.prom'
    overwrite: true
  allocations_storage: !LogStorage
    output_filename: 'metrics/allocations.prom'
    overwrite: true
  allocator: !ResourceAllocator
    action_delay: *action_delay
    mode_config: 'detect'
    agg_period: 20.
    exclusive_cat: False
    database: !ModelDatabase
      db_type: etcd    # 1) local 2)zookeeper 3)etcd
      directory: ~     # required for local
      host: "10.239.157.129:2379"     # required for zookeeper and etcd
      namespace: ~     # for zookeeper, if none, using default model_distribution
      ssl_verify: false     # for etcd, default false
      api_path: "/v3beta"     # for etcd, '/v3alpha' for 3.2.x etcd version, '/v3beta' or '/v3' for 3.3.x etcd version
      timeout: 5.0     # for etcd, default 5.0 seconds
      client_cert_path: ~    # for etcd, default None
      client_key_path: ~     # for etcd, default None
    model_pull_cycle: 180.
  rdt_enabled: True
  extra_labels:
    env_uniq_id: "15"
    own_ip: "100.64.176.15"
```

## Run

Use the commands:

```
sudo -s

// Syscall 'perf_event_open' consumes lots of file descriptors.
// Set an appropriate value.
ulimit -n 65536

// detect contention in work node, use local build model or pull model from central model database
./dist/wca-prm.pex -c wca_detect_prm.yaml -r prm.detector:ContentionDetector -r prm.model_distribution.db:ModelDatabase -l info

// detect contention and allocate task resources in work node, use local build model or pull model from central model database
./dist/wca-prm.pex -c wca_alloc_prm.yaml -r prm.allocator:ResourceAllocator -r prm.model_distribution.db:ModelDatabase -l info
```

## Cluster-level model distribution

To build model in cluster level, each PRM agent need to be configured to make sure the metrics can be stored in a centralized 
Prometheus database. For example, in default configuration, the metrics are configured to be stored in a local file with 
overwrite enabled. user can use a Prometheus Exporter to pull metrics to Prometheus database.  

Also a PRM model builder is required to be deployed in one node, which consumes metrics data in Prometheus database and periodically 
builds models and stores to a distributed configuration service, such as etcd/zookeeper

### train model from prometheus data 

Use the commands to run model builder:

```
./dist/wca-prm.pex -c model_distribution_config.yaml -r prm.model_distribution.build:BuilderRunner -r prm.model_distribution.db:ModelDatabase -r prm.model_distribution.model:DistriModel -l info
```

The default configuration file is ```model_distribution_config.yaml```

```yaml
runner: !BuildRunner
  prometheus_host: "10.239.157.129:9090"
  cycle:    # default 3600s
  time_range:    # defult 86400 seconds
  step:    # prometheus sample step, default 10 seconds
  timeout:     # prometheus request timeout, default 1 seconds
  database: !ModelDatabase
    db_type: etcd    # 1) local 2)zookeeper 3)etcd
    directory: ~     # required for local
    host: "10.239.157.129:2379"     # required for zookeeper and etcd
    namespace: ~     # for zookeeper, if none, using default model_distribution
    ssl_verify: false     # for etcd, default false
    api_path: "/v3beta"     # for etcd, '/v3alpha' for 3.2.x etcd version, '/v3beta' or '/v3' for 3.3.x etcd version
    timeout: 5.0     # for etcd, default 5.0 seconds
    client_cert_path: ~    # for etcd, default None
    client_key_path: ~     # for etcd, default None
  model: !DistriModel
    span: 3
    strict: false
    use_origin: false
    verbose: false
```
### train model from csv data 
run commands

```
./dist/wca-prm.pex -c csv_config.yaml -r prm.model_distribution.csv.builder_csv:BuildRunnerCSV -r prm.model_distribution.db:ModelDatabase -r prm.model_distribution.model:DistriModel -l info
```
csv_config.yaml example:

```yaml
runner: !BuildRunnerCSV
  cycle: 3600    # seconds
  file_path: "data/file.csv"
  database: !ModelDatabase
    db_type: zookeeper
    host: "10.239.157.129:2181"     # required for zookeeper
    namespace: ~     # for zookeeper, if none, using default model_distribution
  model: !DistriModel
    span: 3
    strict: false
    use_origin: false
    verbose: false
```
## Security Consideration 

### Run WCA PRM Agent with Proper Privilege 

WCA PRM agent can be run with non-root user and can be run as systemd service. 
For detail, please refer to installation guide section of WCA project.

### Protect Configuration/Model File

WCA PRM agent uses YAML format configuration file in local file system. Also it 
generates JSON format model file and stores in either local file system or remote
configuraton service, such as etcd/zookeeper.  Tampering of these files may impact
availability of the whole solution. When user deploy the solution, it is highly 
recommended to enable proper access control to these local files or remote 
configuration services.

