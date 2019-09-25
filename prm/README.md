# Intel® PRM plugin for WCA

This readme describes the Intel® Platform Resource Manager (Intel® PRM) plugin
for the Workload Collocation Agent (WCA).

## Table of Contents

- [Introduction](#Introduction)
- [Get started](#Get-started)
- [Build from dockerfile](#Build-from-dockerfile)
- [Security consideration](#Security-consideration)
  - [Run WCA PRM agent with proper privilege](#Run-WCA-PRM-agent-with-proper-privilege)
  - [Protect configuration and model file](#Protect-configuration-and-model-file)


## Introduction

The Intel® PRM plugin for WCA is an analysis and decision engine for WCA. It uses hardware and OS
metrics to build models for each workload in a cluster and use these models to detect resource 
contention on worker node. Also it supports dynamic resource allocation on best-efforts workloads 
to mitigate resource contention on worker node.

For WCA details, please refer to [WCA](https://github.com/intel/workload-collocation-agent).

## Get started

This section describes how to build and deploy WCA with PRM plugin in a cluster. In general, WCA/PRM
Agent needs to be deployed in each worker node, which collects platform metrics, detect resource 
contention and conduct resource allocation if needed. A PRM model builder needs to be deployed 
seperately, which builds workload models and pushes to a configuration service, like zookeeper or etcd.      

[Installation Guide](doc/install.md) introduces how to build WCA with PRM plugin, how to install 
WCA/PRM agent and how to configure agent to work with differen type of job scheduler.

[Model Builder Guide](doc/model.md) introduces how to deploy and configure model builder, including
how to configure model builder to aggregate platform metrics cross nodes and how to configure model
builder to store the models. 

## Build from dockerfile
The Intel® PRM plugin for WCA support build from Dockerfile. To build the project, Please run the command below.
```
// Need Proxy
docker build -t prm:latest --build-arg="http_proxy=$http_proxy" --build-arg="all_proxy=$all_proxy" --build-arg="https_proxy=$https_proxy" .
// No Proxy
sed -i s/--proxy=\\\$https_proxy//g Dockerfile
docker build -t prm:latest .

```
The binary file will be placed at /platform-resource-manager/prm/dist/wca-prm.pex in the image.

## Security consideration 

### Run WCA PRM agent with proper privilege 

WCA PRM agent can be run with non-root user and can be run as systemd service. 
For detail, please refer to installation guide section of WCA project.

### Protect configuration and model file

WCA PRM agent reads YAML format configuration file in local file system and it produces CSV format metrics
data file. Also it generates JSON format model and stores in remote configuraton service, such as etcd/zookeeper. 
Agent does not execute or display the data in any of these files. Tampering of these files may impact availability 
of the whole solution. When user deploys the solution, it is highly recommended to enable proper access control to 
these local files and remote configuration services.
