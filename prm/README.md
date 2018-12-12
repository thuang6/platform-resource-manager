# PRM

## Description
PRM plugin for [Orchestration-aware Workload Collocation Agent](https://github.com/intel/owca)

PRM Plugin is able to collect the hardware and os metrics, build model and detect the contention.

## Required OWCA labels
The PRM plugin needs some labels to be passed to the *detect* API function:
* 'application',
* 'application_version_name'.

The second label is needed as there might be two instances of the same application for which 
seperate statistical models needs to be build. E.g. two instances of twemcache with different 
CPU cores allocated needs seperate models; for that reason the label 'application_version_name' 
have to be different for that two twemcache instances.

## Build

```
git submodule --init owca
tox
```

## Configuration

Default configration file is mesos_prm.yaml

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
```
sudo -s

// Syscall 'perf_event_open' consumes lots of file descriptors. 
// Set an appropriate value. 
ulimit -n 65536 

./dist/owca-prm.pex -c mesos_prm.yaml -r prm.detector:ContentionDetector -l info
```

