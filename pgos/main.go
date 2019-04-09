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

// #cgo CFLAGS: -fstack-protector-strong
// #cgo CFLAGS: -fPIE -fPIC
// #cgo CFLAGS: -O2 -D_FORTIFY_SOURCE=2
// #cgo CFLAGS: -Wformat -Wformat-security
// #cgo LDFLAGS: -lpqos -lm ./perf.o ./pgos.o ./helper.o
// #cgo LDFLAGS: -Wl,-z,noexecstack
// #cgo LDFLAGS: -Wl,-z,relro
// #cgo LDFLAGS: -Wl,-z,now
// #include <pqos.h>
// #include "pgos.h"
// #include "helper.h"
import "C"
import (
	"fmt"
	"os"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

type ModelSpecificEvent uint64

const (
	CYCLE_ACTIVITY_STALLS_L2_MISS ModelSpecificEvent = 0
	CYCLE_ACTIVITY_STALLS_MEM_ANY ModelSpecificEvent = 1
)

const (
	ErrorPqosInitFailure     C.int = 1 << iota
	ErrorCannotOpenCgroup    C.int = 1 << iota
	ErrorCannotOpenTasks     C.int = 1 << iota
	ErrorCannotPerfomSyscall C.int = 1 << iota
)

var coreCount int
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
	Index       int
	Path        string
	Name        string
	Pid         uint32
	File        *os.File `json:"-"`
	Leaders     []uintptr
	Followers   []uintptr
	PgosHandler C.int
}

var pqosEnabled bool = false
var pqosLog *os.File

//export pgos_init
func pgos_init() C.int {
	pqosLog, err := os.OpenFile("/tmp/pqos.log", os.O_CREATE|os.O_WRONLY|os.O_TRUNC, os.ModePerm)
	if err != nil {
		pqosEnabled = false
		return ErrorPqosInitFailure
	}

	config := C.struct_pqos_config{
		fd_log:     C.int(pqosLog.Fd()),
		verbose:    2,
		_interface: C.PQOS_INTER_OS,
	}
	if C.pqos_init(&config) != C.PQOS_RETVAL_OK {
		pqosEnabled = false
		return ErrorPqosInitFailure
	}
	pqosEnabled = true
	return 0
}

//export pgos_finalize
func pgos_finalize() {
	if pqosEnabled {
		pqosLog.Close()
		C.pqos_fini()
	}
}

//export collect
func collect(ctx C.struct_context) C.struct_context {
	ctx.ret = 0
	coreCount = int(ctx.core)

	cgroups := make([]*Cgroup, 0, int(ctx.cgroup_count))

	for i := 0; i < int(ctx.cgroup_count); i++ {
		cg := C.get_cgroup(ctx.cgroups, C.int(i))
		cg.ret = 0
		path, cid := C.GoString(cg.path), C.GoString(cg.cid)
		c, code := NewCgroup(path, cid, i)
		cg.ret |= code
		if c != nil && pqosEnabled {
			cg.ret |= c.GetPgosHandler()
		}
		if cg.ret == 0 {
			cgroups = append(cgroups, c)
		}
	}
	now := time.Now().Unix()
	ctx.timestamp = C.uint64_t(now)
	for j := 0; j < len(cgroups); j++ {
		for k := 0; k < len(cgroups[j].Leaders); k++ {
			cg := C.get_cgroup(ctx.cgroups, C.int(cgroups[j].Index))
			code := StartLeader(cgroups[j].Leaders[k])
			cg.ret |= code
		}
	}
	time.Sleep(time.Duration(ctx.period) * time.Millisecond)
	for j := 0; j < len(cgroups); j++ {
		cg := C.get_cgroup(ctx.cgroups, C.int(cgroups[j].Index))
		res := make([]uint64, len(counters))
		for k := 0; k < coreCount; k++ {
			code := StopLeader(cgroups[j].Leaders[k])
			cg.ret |= code
			result, code := ReadLeader(cgroups[j].Leaders[k])
			cg.ret |= code
			for l := 0; l < len(counters); l++ {
				res[l] += result.Data[l].Value
			}
		}
		if cg.ret != 0 {
			continue
		}

		cg.instructions = C.uint64_t(res[0])
		cg.cycles = C.uint64_t(res[1])
		cg.llc_misses = C.uint64_t(res[2])
		cg.stalls_l2_misses = C.uint64_t(res[3])
		cg.stalls_memory_load = C.uint64_t(res[4])

		if pqosEnabled {
			pgosValue := C.pgos_mon_poll(cgroups[j].PgosHandler)
			cg.llc_occupancy = pgosValue.llc / 1024
			cg.mbm_local = C.double(float64(pgosValue.mbm_local_delta) / 1024.0 / 1024.0 / (float64(ctx.period) / 1000.0))
			cg.mbm_remote = C.double(float64(pgosValue.mbm_remote_delta) / 1024.0 / 1024.0 / (float64(ctx.period) / 1000.0))
		}
		cgroups[j].Close()
	}
	if pqosEnabled {
		C.pgos_mon_stop()
	}
	return ctx
}

func NewCgroup(path string, cid string, index int) (*Cgroup, C.int) {
	cgroupFile, err := os.Open(path)
	if err != nil {
		return nil, ErrorCannotOpenCgroup
	}
	cgroupName := cid
	if cid == "" {
		cgroupNames := strings.Split(strings.Trim(path, string(os.PathSeparator)), string(os.PathSeparator))
		cgroupName = cgroupNames[len(cgroupNames)-1]
	} else {
		cgroupName = cid
	}
	leaders := make([]uintptr, 0, coreCount)
	followers := make([]uintptr, 0, coreCount*(len(counters)-1))

	for i := 0; i < coreCount; i++ {
		l, code := OpenLeader(cgroupFile.Fd(), uintptr(i), counters[0].Type, counters[0].Config)
		if code != 0 {
			return nil, code
		}
		leaders = append(leaders, l)
		for j := 1; j < len(counters); j++ {
			f, code := OpenFollower(l, uintptr(i), counters[j].Type, counters[j].Config)
			if code != 0 {
				return nil, code
			}
			followers = append(followers, f)
		}
	}
	return &Cgroup{
		Index:     index,
		Path:      path,
		Name:      cgroupName,
		File:      cgroupFile,
		Leaders:   leaders,
		Followers: followers,
	}, 0
}

func (this *Cgroup) GetPgosHandler() (code C.int) {
	f, err := os.OpenFile(this.Path+"/tasks", os.O_RDONLY, os.ModePerm)
	if err != nil {
		code = ErrorCannotOpenTasks
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
	if len(pids) == 0 {
		code = ErrorCannotOpenTasks
		return
	}
	this.PgosHandler = C.pgos_mon_start_pids(C.unsigned(len(pids)), (*C.pid_t)(unsafe.Pointer(&pids[0])))

	return
}

func (this *Cgroup) Close() {
	for i := 0; i < len(this.Followers); i++ {
		syscall.Close(int(this.Followers[i]))
	}
	for i := 0; i < len(this.Leaders); i++ {
		syscall.Close(int(this.Leaders[i]))
	}
	this.File.Close()
	return
}

func main() {

}
