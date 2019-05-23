# Intel® PRM plugin

This readme describes the Intel® Platform Resource Manager (Intel® PRM) plugin
for the Workload Collocation Agent (WCA).

## Description

The Intel® PRM plugin uses hardware and OS metrics to build a model and detect
contention.

For WCA details, including an installation guide, refer to [WCA](https://github.com/intel/workload-collocation-agent).

## Required WCA labels

You must pass the following labels to the `detect` API function:

* `application`
* `application_version_name`

The second label is required because multiple instances of the same application
may exist, which requires separate statistical models.

For example, two instances of `twemcache` with different allocated CPU cores
needs separate models. Therefore, the label `application_version_name` must be
different for each of the `twemcache` instances.

## Build

Use the commands:

```
cd ..
git submodule update --init
cd prm
tox
```

## Configuration

The default configuration file is `mesos_prm.yaml`:

```yaml
loggers:
  prm: debug

runner: !DetectionRunner
  action_delay: &action_delay 1.
  node: !MesosNode
  metrics_storage: !LogStorage
    output_filename: /tmp/metrics.log
  anomalies_storage: !LogStorage
    output_filename: /tmp/anomalies.log
  detector: !ContentionDetector
    action_delay: *action_delay
  # Available value: 'collect'/'detect'
  # prm collects data of mesos container and writes the data into a csv file under 'collect' mode.
  # prm will build the model based on the data collected and detect the contention under 'detect' mode.
    mode_config: 'collect'
  # if agg_period value is multiple times of action_delay, prm will aggregate metrics based on agg_period
  # or it will record metrics based on action_delay
    agg_period: 20.
  # prm will detect contention base on the rdt. This configuration must be enabled.
  rdt_enabled: True
  # key value pairs to tag the data
  extra_labels:
    own_ip: "10.3.88.120"
```


## Run

Use the commands:

```
sudo -s

// Syscall 'perf_event_open' consumes lots of file descriptors.
// Set an appropriate value.
ulimit -n 65536

./dist/wca-prm.pex -c mesos_prm.yaml -r prm.detector:ContentionDetector -l info
```

## Cluster-level model distribution

Use the commands:

```
./dist/wca-prm.pex -c model_distribution_config.yaml -r prm.model_distribution.build:BuilderRunner -r prm.model_distribution.db:ModelDatabase -r prm.model_distribution.model:DistriModel -l info
```

The default configuration file is ```model_distribution_config.yaml```

```yaml
loggers:
  prm: debug

runner: !BuilderRunner
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