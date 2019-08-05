package main

import (
	"testing"
)

func TestGetCgroupDriver(t *testing.T) {
	newDockerClient()
	readCgroupDriver()
	if cgroupDriver != "cgroupfs" {
		t.Fatalf("Failed to get cgroup driver: %s", cgroupDriver)
	}
}
