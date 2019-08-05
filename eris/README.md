# Eris
## Support feature
* perf event configurable
* metrics polling
## Usage
```
go get -d github.intel.com/wangjial/eris
cd go/src/github.intel.com/wangjial/eris # if $GOPATH is not set
cd $GOPATH/src/github.intel.com/wangjial/eris # if $GOPATH is set
make
sudo ./eris -collect-metrics -metric-file metric.csv
```
## Troubleshooting

### panic: Error response from daemon: client version 1.41 is too new. Maximum supported API version is 1.38

Run eris with env DOCKER_API_VERSION
```
sudo DOCKER_API_VERSION=1.38 ./eris -collect-metrics
```