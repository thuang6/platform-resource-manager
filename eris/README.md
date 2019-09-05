# Eris
## Support feature
* perf event configurable
* metrics polling
## Usage
```
go get -d github.com/intel/platform-resource-manager/eris
cd ~/go/src/github.com/intel/platform-resource-manager/eris # if $GOPATH is not set
cd $GOPATH/src/github.com/intel/platform-resource-manager/eris # if $GOPATH is set
make
sudo ./eris -record-metric -record-util -prometheus-port 8080 -detect workload.json
```
## Troubleshooting

### panic: Error response from daemon: client version 1.41 is too new. Maximum supported API version is 1.38

Run eris with env DOCKER_API_VERSION
```
sudo DOCKER_API_VERSION=1.38 ./eris -record-metric -record-util -prometheus-port 8080 -detect workload.json
```