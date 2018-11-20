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
// 
package main

// #include <stdint.h>
// #include <sys/types.h>
// #include <linux/perf_event.h>
// #include "perf.c"
// uint32_t def_PERF_ATTR_SIZE_VER5 = PERF_ATTR_SIZE_VER5;
//
// void set_attr_disabled(struct perf_event_attr *attr, int disabled) {
// 		attr->disabled = disabled;
// }
import "C"
import (
	"bytes"
	"encoding/binary"
	"log"
	"syscall"
	"unsafe"
)

func perfEventOpen(attr C.struct_perf_event_attr,
	pid, cpu, groupFd, flags uintptr) uintptr {
	fd, _, err := syscall.Syscall6(syscall.SYS_PERF_EVENT_OPEN, uintptr(unsafe.Pointer(&attr)),
		pid, cpu, groupFd, flags, 0)
	if err != 0 {
		log.Fatalf("syscall failed with error code %+v", err)
	}
	return fd
}

func ioctl(fd, req, arg uintptr) {
	_, _, err := syscall.Syscall(syscall.SYS_IOCTL, fd, req, arg)
	if err != 0 {
		log.Fatalf("syscall failed with error code %+v", err)
	}
	return
}

type PerfStruct struct {
	Size        uint64
	TimeEnabled uint64
	TimeRunning uint64
	Data        [5]struct {
		Value uint64
		ID    uint64
	}
}

func OpenLeader(cgroupFd uintptr, cpu uintptr, perfType C.uint32_t, perfConfig C.uint64_t) uintptr {
	leaderAttr := C.struct_perf_event_attr{
		_type:       perfType,
		size:        C.def_PERF_ATTR_SIZE_VER5,
		config:      C.ulonglong(C.get_config_of_event(perfType, perfConfig)),
		sample_type: C.PERF_SAMPLE_IDENTIFIER,
		read_format: C.PERF_FORMAT_GROUP |
			C.PERF_FORMAT_TOTAL_TIME_ENABLED |
			C.PERF_FORMAT_TOTAL_TIME_RUNNING |
			C.PERF_FORMAT_ID,
	}
	C.set_attr_disabled(&leaderAttr, 1)
	return perfEventOpen(leaderAttr, cgroupFd, cpu, ^uintptr(0), C.PERF_FLAG_PID_CGROUP|C.PERF_FLAG_FD_CLOEXEC)
}

func OpenFollower(leader uintptr, cpu uintptr, perfType C.uint32_t, perfConfig C.uint64_t) uintptr {
	followerAttr := C.struct_perf_event_attr{
		_type:       perfType,
		size:        C.def_PERF_ATTR_SIZE_VER5,
		config:      C.ulonglong(C.get_config_of_event(perfType, perfConfig)),
		sample_type: C.PERF_SAMPLE_IDENTIFIER,
		read_format: C.PERF_FORMAT_GROUP |
			C.PERF_FORMAT_TOTAL_TIME_ENABLED |
			C.PERF_FORMAT_TOTAL_TIME_RUNNING |
			C.PERF_FORMAT_ID,
	}
	C.set_attr_disabled(&followerAttr, 0)
	return perfEventOpen(followerAttr, ^uintptr(0), cpu, leader, C.PERF_FLAG_FD_CLOEXEC)
}

func StartLeader(leader uintptr) {
	ioctl(leader, C.PERF_EVENT_IOC_RESET, 0)
	ioctl(leader, C.PERF_EVENT_IOC_ENABLE, 0)
}

func StopLeader(leader uintptr) {
	ioctl(leader, C.PERF_EVENT_IOC_DISABLE, 0)
}

func ReadLeader(leader uintptr) PerfStruct {
	b := make([]byte, 1000)
	_, err := syscall.Read(int(leader), b)
	if err != nil {
		log.Fatal(err)
	}
	var result PerfStruct
	binary.Read(bytes.NewBuffer(b), binary.LittleEndian, &result)
	for i := 0; i < len(result.Data); i++ {
		if result.TimeEnabled == 0 {
			result.Data[i].Value = 0
		} else {
			result.Data[i].Value = uint64(float64(result.Data[i].Value) / float64(result.TimeRunning) * float64(result.TimeEnabled))
		}
	}
	return result
}
