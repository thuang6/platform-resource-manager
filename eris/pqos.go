package main

// #include <pqos.h>
// #include <stdlib.h>
// struct pqos_mon_data* new_pqos_mon_data() {
// 		return malloc(sizeof(struct pqos_mon_data));
// }
// void free_pqos_mon_data(struct pqos_mon_data* data) {
// 		free(data);
// }
import "C"

import (
	"fmt"
	"log"
	"os"
	"runtime"
	"unsafe"
)

var pqosEnabled bool
var pqosGroups = map[string]*C.struct_pqos_mon_data{}

func init() {
	config := C.struct_pqos_config{
		fd_log:     2,
		verbose:    -1,
		_interface: C.PQOS_INTER_OS,
	}
	ec := C.pqos_init(&config)
	if ec != C.PQOS_RETVAL_OK {
		log.Printf("pqos init error code: %d\n", ec)
		return
	}
	pqosEnabled = true
	return
}

func freePqosGroup(id string) {
	C.free_pqos_mon_data(pqosGroups[id])
}

func newPqosGroup(id string, mapPids map[C.pid_t]bool) (*C.struct_pqos_mon_data, error) {
	if !pqosEnabled {
		return nil, nil
	}
	pids := make([]C.pid_t, 0, len(mapPids))
	for pid := range mapPids {
		pids = append(pids, pid)
	}
	pqosData := C.new_pqos_mon_data()

	cpus := runtime.NumCPU()
	cpulist := make([]C.unsigned, cpus)
	for i := 0; i < cpus; i++ {
		cpulist[i] = C.unsigned(i)
	}
	ec := C.pqos_mon_start(C.unsigned(runtime.NumCPU()), (*C.unsigned)(unsafe.Pointer(&cpulist[0])),
		C.PQOS_MON_EVENT_L3_OCCUP|C.PQOS_MON_EVENT_LMEM_BW|C.PQOS_MON_EVENT_RMEM_BW,
		nil, pqosData)
	if ec != C.PQOS_RETVAL_OK {
		return nil, fmt.Errorf("failed to start monitor pqos, error code %+v", ec)
	}

	ec = C.pqos_mon_add_pids(C.unsigned(len(pids)), (*C.pid_t)(unsafe.Pointer(&pids[0])), pqosData)
	if ec != C.PQOS_RETVAL_OK {
		return nil, fmt.Errorf("failed to add pqos pids, error code %+v", ec)
	}
	pqosGroups[id] = pqosData
	return pqosData, nil
}

func removePqosGroup(id string) {
	if !pqosEnabled {
		return
	}
	C.pqos_mon_stop(pqosGroups[id])
	delete(pqosGroups, id)
}

func updatePqosGroup(data *C.struct_pqos_mon_data, old, new map[C.pid_t]bool) error {
	if !pqosEnabled {
		return nil
	}
	removePids := []C.pid_t{}
	addPids := []C.pid_t{}
	for oldPid := range old {
		if _, ok := new[oldPid]; !ok {
			removePids = append(removePids, oldPid)
		}
	}
	for newPid := range new {
		if _, ok := old[newPid]; !ok {
			addPids = append(addPids, newPid)
		}
	}
	if len(removePids) > 0 {
		ec := C.pqos_mon_remove_pids(C.unsigned(len(removePids)), (*C.pid_t)(unsafe.Pointer(&removePids[0])), data)
		if ec != C.PQOS_RETVAL_OK {
			return fmt.Errorf("failed to remove pqos pids, error code %+v", ec)
		}
	}
	if len(addPids) > 0 {
		ec := C.pqos_mon_add_pids(C.unsigned(len(addPids)), (*C.pid_t)(unsafe.Pointer(&addPids[0])), data)
		if ec != C.PQOS_RETVAL_OK {
			return fmt.Errorf("failed to add pqos pids, error code %+v", ec)
		}
	}
	return nil
}

// pollPqos will poll all containers data
func pollPqos(data *C.struct_pqos_mon_data) error {
	ec := C.pqos_mon_poll((**C.struct_pqos_mon_data)(unsafe.Pointer(&data)), 1)
	if ec != C.PQOS_RETVAL_OK {
		return fmt.Errorf("failed to poll pqos, error code %+v", ec)
	}
	return nil
}

func listTaskPid(id string) (map[C.pid_t]bool, error) {
	f, err := os.OpenFile(getCgroupPath(id)+"/tasks", os.O_RDONLY, os.ModePerm)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	mapPids := map[C.pid_t]bool{}
	for {
		var pid uint32
		n, err := fmt.Fscanf(f, "%d\n", &pid)
		if n == 0 || err != nil {
			break
		}
		mapPids[C.pid_t(pid)] = true
	}
	return mapPids, nil
}
