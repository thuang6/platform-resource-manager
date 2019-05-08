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

```
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

