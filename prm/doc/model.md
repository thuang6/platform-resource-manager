# PRM Model Builder Guide

## Table of Contents

- [Introduction](#Introduction)
- [Train model from data in Prometheus database](#Train-model-from-data-in-Prometheus-database)
- [Train model from csv data](#Train-model-from-csv-data)

## Introduction

To train model in cluster level, each WCA/PRM agent need to be configured to make sure the metrics can be stored in a centralized 
Prometheus database. For example, in default configuration, the metrics are configured to be stored in a local file with 
overwrite enabled. user can use a Prometheus Exporter to export metrics to Prometheus database.  

Also a PRM model builder (use the same executable binary `./dist/wca-prm.pex`) is required to be deployed in one node, which consumes metrics 
data in Prometheus database and periodically trains models and stores in a distributed configuration service, such as etcd/zookeeper.

In case there is no Prometheus database service available in user environment, model builder also support user triggered model training from a csv file, which requires user combines all csv files collected from each node into single csv file in advance.
 
## Train model from data in Prometheus database 

Use the commands to run model builder:

```
// for security reason, WCA requires absolute file path for configuration
./dist/wca-prm.pex -c $PWD/model_distribution_config.yaml -r prm.model_distribution.prometheus.builder_prom:BuildRunnerProm -r prm.model_distribution.db:ModelDatabase -r prm.model_distribution.model:DistriModel -l info
```

The default configuration file is ```model_distribution_config.yaml```

```yaml
runner: !BuildRunner
  prometheus_host: "10.239.157.129:9090"
  cycle:    # default 3600s
  time_range:    # defult 86400 secondsrunner: !BuildRunner
  prometheus_host: "10.239.157.129:9090"
  cycle:    # default 3600s
  time_range:    # defult 86400 seconds
  step:    # prometheus sample step, default 10 seconds
  timeout:     # prometheus request timeout, default 1 seconds
  database: !ModelDatabase
    db_type: etcd    # 1) local 2)zookeeper 3)etcd
    host: "10.239.157.1291:2379"     # required for zookeeper and etcd
    namespace: ~
    directory: ~
    api_path: "/v3beta"     # for etcd, '/v3alpha' for 3.2.x etcd version, '/v3beta' or '/v3' for 3.3.x etcd version
    timeout: 5.0     # for etcd, default 5.0 seconds
    ssl: !SSL 
      server_verify: false
      client_cert_path: ~
      client_key_path: ~
  model: !DistriModel
    span: 3
    strict: false
    use_origin: false
    verbose: false
```

## Train model from csv data 

run commands

```
// for security reason, WCA requires absolute file path for configuration
./dist/wca-prm.pex -c $PWD/csv_config.yaml -r prm.model_distribution.csv.builder_csv:BuildRunnerCSV -r prm.model_distribution.db:ModelDatabase -r prm.model_distribution.model:DistriModel -l info
```
csv_config.yaml example:

```yaml
runner: !BuildRunnerCSV
  file_path: "data/file.csv"
  database: !ModelDatabase
    db_type: zookeeper    # 1) local 2)zookeeper 3)etcd
    host: "10.239.157.129:2181"     # required for zookeeper and etcd
    namespace: ~     # for zookeeper, if none, using default model_distribution
    timeout: 5.0
    ssl: !SSL
      server_verify: false
      client_cert_path: ~
      client_key_path: ~
  model: !DistriModel
    span: 3
    strict: false
    use_origin: false
    verbose: false
```
