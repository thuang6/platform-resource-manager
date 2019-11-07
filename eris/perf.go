package main

// #include <unistd.h>
// #include <sys/types.h>
// #include <linux/perf_event.h>
// #include <stdint.h>
// #include <errno.h>
//
// uint32_t def_PERF_ATTR_SIZE_VER5 = PERF_ATTR_SIZE_VER5;
//
// void set_attr_disabled(struct perf_event_attr *attr, int disabled) {
// 	attr->disabled = disabled;
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
	switch platform {
	case "BDX":
		handlePerfEventConfig(bdxJSON)
	case "SLX":
		handlePerfEventConfig(skxJSON)
	case "CLX":
		handlePerfEventConfig(clxJSON)
	}
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
