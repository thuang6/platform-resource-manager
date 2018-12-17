# Intel® PRM plugin

This readme describes the Intel® Platform Resource Manager (Intel® PRM) plugin
for the Orchestration-aware Workload Collocation Agent (OWCA).

## Description

The Intel® PRM plugin uses hardware and OS metrics to build a model and detect
contention.

For OWCA details, including an installation guide, refer to [OWCA](https://github.com/intel/owca).

## Required OWCA labels

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
git submodule update --init owca
tox
```

## Configuration

The default configuration file is `mesos_prm.yaml`:

```
loggers:
  prm: debug

runner: !DetectionRunner
  node: !MesosNode
  action_delay: 20.
  metrics_storage: !LogStorage
    output_filename: /tmp/metrics.log
  anomalies_storage: !LogStorage
    output_filename: /tmp/anomalies.log
  detector: !ContentionDetector
  # Available value: 'collect'/'detect'
  # prm collects data of mesos container and writes the data into a csv file under 'collect' mode.
  # prm will build the model based on the data collected and detect the contention under 'detect' mode.
    mode_config: 'collect'
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

./dist/owca-prm.pex -c mesos_prm.yaml -r prm.detector:ContentionDetector -l info
```

