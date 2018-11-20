// Copyright (C) 2018 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions
// and limitations under the License.
//
//
// SPDX-License-Identifier: Apache-2.0

package main

// #include <stdint.h>
// #include <sys/types.h>
// #include <linux/perf_event.h>
// #cgo LDFLAGS: -lpqos -lm
// #include <pqos.h>
// #include "pgos.c"
// int LOG_VER_SUPER_VERBOSE = 2;
import "C"
import (
	"flag"
	"fmt"
	"os"
	"strings"
	"time"
	"unsafe"
)

type ModelSpecificEvent uint64

const (
	CYCLE_ACTIVITY_STALLS_L2_MISS ModelSpecificEvent = 0
	CYCLE_ACTIVITY_STALLS_MEM_ANY ModelSpecificEvent = 1
)

var coreCount = flag.Int("core", 1, "core count")
var cycle = flag.Int("cycle", 1, "monitor time")
var frequency = flag.Int64("frequency", 5, "sample frequency")
var period = flag.Int64("period", 1, "sample period")
var cgroupPath = flag.String("cgroup", "", "cgroups to be monitored")
var containerIds = flag.String("cids", "", "container id list")
var metricsDescription = []string{"instructions", "cycles", "LLC misses", "stalls L2 miss", "stalls memory load"}

type PerfCounter struct {
	Type   C.uint32_t
	Config C.uint64_t
}

var counters = []PerfCounter{
	PerfCounter{Type: C.PERF_TYPE_HARDWARE, Config: C.PERF_COUNT_HW_INSTRUCTIONS},
	PerfCounter{Type: C.PERF_TYPE_HARDWARE, Config: C.PERF_COUNT_HW_CPU_CYCLES},
	PerfCounter{Type: C.PERF_TYPE_HARDWARE, Config: C.PERF_COUNT_HW_CACHE_MISSES},
	PerfCounter{Type: C.PERF_TYPE_RAW, Config: C.uint64_t(CYCLE_ACTIVITY_STALLS_L2_MISS)},
	PerfCounter{Type: C.PERF_TYPE_RAW, Config: C.uint64_t(CYCLE_ACTIVITY_STALLS_MEM_ANY)},
}

type Cgroup struct {
	Path        string
	Name        string
	Pid         uint32
	File        *os.File `json:"-"`
	Leaders     []uintptr
	Followers   []uintptr
	PgosHandler C.int
}

func NewCgroup(path string, cid string) (*Cgroup, error) {
	cgroupFile, err := os.Open(path)
	if err != nil {
		println(path)
		return nil, err
	}
	cgroupName := cid
	if cid == "" {
		cgroupNames := strings.Split(strings.Trim(path, string(os.PathSeparator)), string(os.PathSeparator))
		cgroupName = cgroupNames[len(cgroupNames)-1]
	} else {
		cgroupName = cid
	}
	leaders := make([]uintptr, 0, *coreCount)
	followers := make([]uintptr, 0, *coreCount*(len(counters)-1))

	for i := 0; i < *coreCount; i++ {
		l := OpenLeader(cgroupFile.Fd(), uintptr(i), counters[0].Type, counters[0].Config)
		leaders = append(leaders, l)
		for j := 1; j < len(counters); j++ {
			f := OpenFollower(l, uintptr(i), counters[j].Type, counters[j].Config)
			followers = append(followers, f)
		}
	}
	return &Cgroup{
		Path:      path,
		Name:      cgroupName,
		File:      cgroupFile,
		Leaders:   leaders,
		Followers: followers,
	}, nil
}

func (this *Cgroup) GetPgosHandler() {
	f, err := os.OpenFile(this.Path+"/tasks", os.O_RDONLY, os.ModePerm)
	if err != nil {
		println(err.Error())
		return
	}
	defer f.Close()
	pids := []C.pid_t{}
	for {
		var pid uint32
		n, err := fmt.Fscanf(f, "%d\n", &pid)
		if n == 0 || err != nil {
			break
		}
		pids = append(pids, C.pid_t(pid))
	}
	this.PgosHandler = C.pgos_mon_start_pids(C.unsigned(len(pids)), (*C.pid_t)(unsafe.Pointer(&pids[0])))

	return
}

func (this *Cgroup) Close() error {
	err := this.File.Close()
	if err != nil {
		return err
	}
	return nil
}

func main() {
	pqosLog, err := os.OpenFile("/tmp/pqos.log", os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.ModePerm)
	if err != nil {
		println(err.Error())
		return
	}
	defer pqosLog.Close()

	config := C.pqos_config{
		fd_log:     C.int(pqosLog.Fd()),
		verbose:    C.LOG_VER_SUPER_VERBOSE,
		_interface: C.PQOS_INTER_OS,
	}
	C.pqos_init(&config)

	flag.Parse()
	cgroupsPath := strings.Split(*cgroupPath, ",")
	var conIds = []string{}
	if *containerIds != "" {
		conIds = strings.Split(*containerIds, ",")
	}
	cgroups := make([]*Cgroup, 0, len(cgroupsPath))
	fds := make([]int32, 0, len(cgroupsPath))
	for i := 0; i < len(cgroupsPath); i++ {
		cid := ""
		if *containerIds != "" {
			cid = conIds[i]
		}
		c, err := NewCgroup(cgroupsPath[i], cid)
		if err != nil {
			println(err.Error())
			continue
		}
		c.GetPgosHandler()
		cgroups = append(cgroups, c)
		fds = append(fds, int32(c.File.Fd()))
	}

	frequencyDuration := fmt.Sprintf("%ds", *frequency-(*period))
	monitorDuration := fmt.Sprintf("%ds", *period)
	fd, err := time.ParseDuration(frequencyDuration)
	md, err := time.ParseDuration(monitorDuration)
	if err != nil {
		println(err.Error())
		return
	}
	for i := 0; i < *cycle; i++ {
		now := time.Now().Unix()
		for j := 0; j < len(cgroups); j++ {
			for k := 0; k < len(cgroups[j].Leaders); k++ {
				StartLeader(cgroups[j].Leaders[k])
			}
		}
		time.Sleep(md)
		for j := 0; j < len(cgroups); j++ {
			res := make([]uint64, len(counters))
			for k := 0; k < *coreCount; k++ {
				StopLeader(cgroups[j].Leaders[k])
				result := ReadLeader(cgroups[j].Leaders[k])
				for l := 0; l < len(counters); l++ {
					res[l] += result.Data[l].Value
				}
			}
			for k := 0; k < len(counters); k++ {
				fmt.Printf("%s\t%s\t%d\t%+v\n", cgroups[j].Name, metricsDescription[k], now, res[k])
			}
		}
		for j := 0; j < len(cgroups); j++ {
			pgosValue := C.pgos_mon_poll(cgroups[j].PgosHandler)
			fmt.Printf("%s\t%s\t%d\t%+v\n", cgroups[j].Name, "LLC occupancy", now, pgosValue.llc/1024)
			fmt.Printf("%s\t%s\t%d\t%+v\n", cgroups[j].Name, "Memory bandwidth local", now, float64(pgosValue.mbm_local_delta)/1024.0/1024.0/float64(*period))
			fmt.Printf("%s\t%s\t%d\t%+v\n", cgroups[j].Name, "Memory bandwidth remote", now, float64(pgosValue.mbm_remote_delta)/1024.0/1024.0/float64(*period))
		}
		time.Sleep(fd)
	}
	C.pgos_mon_stop()
	C.pqos_fini()
	return
}
