package main

import (
	"context"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/client"
)

var dockerClient *client.Client
var cgroupDriver string

func newDockerClient() {
	var err error
	dockerClient, err = client.NewEnvClient()
	if err != nil {
		panic(err)
	}
}

func readCgroupDriver() {
	info, err := dockerClient.Info(context.TODO())
	if err != nil {
		panic(err)
	}
	cgroupDriver = info.CgroupDriver
}

// return container and its name
func getContainers() (map[string]string, error) {
	ret := map[string]string{}
	list, err := dockerClient.ContainerList(context.TODO(), types.ContainerListOptions{})
	if err != nil {
		return nil, err
	} else {
		for i := 0; i < len(list); i++ {
			ret[list[i].ID] = list[i].Names[0]
		}
		return ret, nil
	}
}

func getCgroupPath(id string) string {
	switch cgroupDriver {
	case "cgroupfs":
		return "/sys/fs/cgroup/perf_event/docker/" + id
	case "systemd":
		return "/sys/fs/cgroup/perf_event/system.slice/docker-" + id + ".scope"
	default:
		return ""
	}
}

func getCgroupCPUPath(id string) string {
	switch cgroupDriver {
	case "cgroupfs":
		return "/sys/fs/cgroup/cpu/docker/" + id + "/cpuacct.usage"
	case "systemd":
		return "/sys/fs/cgroup/cpu/system.slice/docker-" + id + ".scope/cpuacct.usage"
	default:
		return ""
	}
}
