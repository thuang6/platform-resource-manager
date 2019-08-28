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
// #include <unistd.h>
// #include <cpuid.h>
// #include <asm/unistd.h>
// #include <stdint.h>
// #include <errno.h>
//
// uint32_t def_PERF_ATTR_SIZE_VER5 = PERF_ATTR_SIZE_VER5;
// int UNKNOWN = 0;
// int BROADWELL = 1;
// int SKYLAKE = 2;
// int CASCADELAKE = 3;
//
// void set_attr_disabled(struct perf_event_attr *attr, int disabled) {
// 	attr->disabled = disabled;
// }
// int get_cpu_family() {
// 		uint32_t eax, ebx, ecx, edx;
// 		__cpuid(1, eax, ebx, ecx, edx);
// 		const uint32_t model = (eax >> 4) & 0xF;
// 		const uint32_t family = (eax >> 8) & 0xF;
// 		const uint32_t extended_model = (eax >> 16) & 0xF;
// 		const uint32_t extended_family = (eax >> 20) & 0xFF;
//		const uint32_t stepping = eax & 0xF;
// 		uint32_t display_family = family;
// 		if (family == 0xF) {
// 			display_family += extended_family;
// 		}
// 		uint32_t display_model = model;
// 		if ((family == 0x6) || (family == 0xF)) {
// 			display_model += extended_model << 4;
// 		}
// 		if (display_family == 0x06) {
// 			switch (display_model) {
// 				case 0x4E:
// 				case 0x5E:
// 					return SKYLAKE;
// 				case 0x55:
//					switch (stepping) {
//						case 0x4:
//							return SKYLAKE;
//						case 0x5:
//						case 0x6:
//						case 0x7:
//							return CASCADELAKE;
//					}
// 				case 0x3D:
// 				case 0x47:
// 				case 0x4F:
// 				case 0x56:
// 					return BROADWELL;
// 			}
// 		}
// 		return UNKNOWN;
// }
import "C"
import (
	"bytes"
	"encoding/binary"
	"errors"
	"syscall"
	"unsafe"
)

func initPerf() {
	var conf []byte
	family := C.get_cpu_family()
	switch family {
	case C.BROADWELL:
		conf = bdxJSON
	case C.SKYLAKE:
		conf = skxJSON
	case C.CASCADELAKE:
		conf = clxJSON
	default:
		panic(errors.New("unknown platform"))
	}
	handlePerfEventConfig(conf)
}

type PerfEventCounter struct {
	EventCode, UMask                      uint
	EventName                             string
	CounterMask, Invert, EdgeDetect, PEBS uint
}

var peCounters = []PerfEventCounter{}

func (pec *PerfEventCounter) getConfig() C.__u64 {
	return C.__u64(pec.EventCode |
		(pec.UMask << 8) |
		(pec.EdgeDetect << 18) |
		(pec.Invert << 23) |
		(pec.CounterMask << 24))
}

func perfEventOpen(attr C.struct_perf_event_attr,
	pid, cpu, groupFd, flags uintptr) (uintptr, error) {
	fd, _, err := syscall.Syscall6(syscall.SYS_PERF_EVENT_OPEN, uintptr(unsafe.Pointer(&attr)),
		pid, cpu, groupFd, flags, 0)
	if err != 0 {
		return 0, errors.New("fail to open perf event")
	}
	return fd, nil
}

func ioctl(fd, req, arg uintptr) error {
	_, _, err := syscall.Syscall(syscall.SYS_IOCTL, fd, req, arg)
	if err != 0 {
		return errors.New("fail to ioctl")
	}
	return nil
}

type perfStruct struct {
	Size        uint64
	TimeEnabled uint64
	TimeRunning uint64
	Data        [10]struct {
		Value uint64
		ID    uint64
	}
}

func openPerfLeader(cgroupFd uintptr, cpu uintptr, pec PerfEventCounter) (uintptr, error) {
	perfAttr := C.struct_perf_event_attr{
		_type:       C.__u32(C.PERF_TYPE_RAW),
		size:        C.__u32(C.def_PERF_ATTR_SIZE_VER5),
		config:      pec.getConfig(),
		sample_type: C.PERF_SAMPLE_IDENTIFIER,
		read_format: C.PERF_FORMAT_GROUP |
			C.PERF_FORMAT_TOTAL_TIME_ENABLED |
			C.PERF_FORMAT_TOTAL_TIME_RUNNING |
			C.PERF_FORMAT_ID,
	}
	C.set_attr_disabled(&perfAttr, 1)
	return perfEventOpen(perfAttr, cgroupFd, cpu, ^uintptr(0), C.PERF_FLAG_PID_CGROUP|C.PERF_FLAG_FD_CLOEXEC)
}

func openPerfFollower(leader uintptr, cgroupFd uintptr, cpu uintptr, pec PerfEventCounter) (uintptr, error) {
	perfAttr := C.struct_perf_event_attr{
		_type:       C.__u32(C.PERF_TYPE_RAW),
		size:        C.__u32(C.def_PERF_ATTR_SIZE_VER5),
		config:      pec.getConfig(),
		sample_type: C.PERF_SAMPLE_IDENTIFIER,
		read_format: C.PERF_FORMAT_GROUP |
			C.PERF_FORMAT_TOTAL_TIME_ENABLED |
			C.PERF_FORMAT_TOTAL_TIME_RUNNING |
			C.PERF_FORMAT_ID,
	}
	C.set_attr_disabled(&perfAttr, 1)
	return perfEventOpen(perfAttr, ^uintptr(0), cpu, leader, C.PERF_FLAG_FD_CLOEXEC)
}

func startPerf(fd uintptr) error {
	err := ioctl(fd, C.PERF_EVENT_IOC_RESET, 0)
	if err != nil {
		return err
	}
	err = ioctl(fd, C.PERF_EVENT_IOC_ENABLE, 0)
	if err != nil {
		return err
	}
	return nil
}

func stopPerf(fd uintptr) error {
	return ioctl(fd, C.PERF_EVENT_IOC_DISABLE, 0)
}

func readPerf(fd uintptr) ([]uint64, uint64, uint64, error) {
	res := make([]uint64, len(peCounters))
	b := make([]byte, 1000)
	_, err := syscall.Read(int(fd), b)
	if err != nil {
		return nil, 0, 0, err
	}
	var result perfStruct
	binary.Read(bytes.NewBuffer(b), binary.LittleEndian, &result)

	for i := 0; i < len(res); i++ {
		res[i] += result.Data[i].Value
	}

	return res, result.TimeEnabled, result.TimeRunning, nil
}
