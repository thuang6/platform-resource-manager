package main

// #include <pqos.h>
// #include <stdlib.h>
// enum pqos_cdp_config l3cdp_default = PQOS_REQUIRE_CDP_ANY;
// enum pqos_cdp_config l2cdp_default = PQOS_REQUIRE_CDP_ANY;
// enum pqos_cdp_config mba_default = PQOS_MBA_ANY;
// struct pqos_mon_data* new_pqos_mon_data() {
// 		return malloc(sizeof(struct pqos_mon_data));
// }
// void free_pqos_mon_data(struct pqos_mon_data* data) {
// 		free(data);
// }
//
// void set_l3ca_mask(struct pqos_l3ca *cat, uint64_t mask) {
// 		cat->u.ways_mask = mask;
// }
//
// unsigned arr_index(unsigned* arr, uint index) {
// 		return arr[index];
// }
//
// struct pqos_cpuinfo *cpu_info = NULL;
// struct pqos_cap *cpu_cap = NULL;
// unsigned *mba_ids = NULL, *cat_ids = NULL;
// unsigned cat_id_count, mba_id_count;
// void fin_free() {
//		if (cpu_info != NULL) {
//			free(cpu_info);
//		}
//		if (cpu_cap != NULL) {
//			free(cpu_cap);
//		}
//		if (mba_ids != NULL) {
//			free(mba_ids);
//		}
//		if (cat_ids != NULL) {
//			free(cat_ids);
//		}
// }
import "C"

import (
	"fmt"
	"log"
	"os"
	"unsafe"
)

var pqosEnabled bool
var pqosGroups = map[string]*C.struct_pqos_mon_data{}

const bestEffortCOS = 2
const latencyCriticalCOS = 1
const genericCOS = 0

var catSupported, mbaSupported bool

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

	ec = C.pqos_cap_get(&C.cpu_cap, &C.cpu_info)
	if ec != C.PQOS_RETVAL_OK {
		log.Printf("pqos get capability error code: %d\n", ec)
		return
	}

	var supported, enabled C.int
	if ec := C.pqos_l3ca_cdp_enabled(C.cpu_cap, &supported, &enabled); ec == C.PQOS_RETVAL_OK && supported != 0 {
		catSupported = true
	} else {
		log.Printf("pqos not support CAT")
	}
	if ec := C.pqos_mba_ctrl_enabled(C.cpu_cap, &supported, &enabled); ec == C.PQOS_RETVAL_OK && supported != 0 {
		mbaSupported = true
	} else {
		log.Printf("pqos not support MBA")
	}

	C.cat_ids = C.pqos_cpu_get_l3cat_ids(C.cpu_info, &C.cat_id_count)
	if C.cat_ids == nil {
		log.Printf("pqos get l3cat id failed\n")
		return
	}
	C.mba_ids = C.pqos_cpu_get_mba_ids(C.cpu_info, &C.mba_id_count)
	if C.mba_ids == nil {
		log.Printf("pqos get mba id failed\n")
		return
	}
	pqosEnabled = true
	return
}

func pqosFin() {
	//	C.fin_free()
	if ec := C.pqos_alloc_reset(C.l3cdp_default, C.l2cdp_default, C.mba_default); ec != C.PQOS_RETVAL_OK {
		log.Printf("pqos reset configuration error %d", ec)
	}
	if ec := C.pqos_fini(); ec != C.PQOS_RETVAL_OK {
		log.Printf("pqos fini error %d", ec)
	}
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

	ec := C.pqos_mon_start_pids(C.unsigned(len(pids)), (*C.pid_t)(unsafe.Pointer(&pids[0])), C.PQOS_MON_EVENT_L3_OCCUP|C.PQOS_MON_EVENT_LMEM_BW|C.PQOS_MON_EVENT_RMEM_BW, nil, pqosData)
	if ec != C.PQOS_RETVAL_OK {
		return nil, fmt.Errorf("failed to start pqos pids, error code %+v", ec)
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

func updatePqosGroup(data *C.struct_pqos_mon_data, cos uint, old, new map[C.pid_t]bool) error {
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
		if cos != genericCOS {
			ec := C.pqos_alloc_assoc_set_pid(newPid, C.unsigned(cos))
			if ec != C.PQOS_RETVAL_OK {
				log.Printf("failed to associate pqos pids to COS #%d, error code %+v", cos, ec)
			}
		}
	}

	if len(removePids) > 0 {
		ec := C.pqos_mon_remove_pids(C.unsigned(len(removePids)), (*C.pid_t)(unsafe.Pointer(&removePids[0])), data)
		if ec != C.PQOS_RETVAL_OK {
			log.Printf("failed to remove pqos pids, error code %+v", ec)
		}
		ec = C.pqos_alloc_release_pid((*C.pid_t)(unsafe.Pointer(&removePids[0])), C.unsigned(len(removePids)))
		if ec != C.PQOS_RETVAL_OK {
			// ignore error
			// log.Printf("failed to reassign pqos pids to COS #0, error code %+v", ec)
		}
	}
	if len(addPids) > 0 {
		ec := C.pqos_mon_add_pids(C.unsigned(len(addPids)), (*C.pid_t)(unsafe.Pointer(&addPids[0])), data)
		if ec != C.PQOS_RETVAL_OK {
			log.Printf("failed to add pqos pids, error code %+v", ec)
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
	f, err := os.OpenFile(getCgroupPath(id)+"/cgroup.procs", os.O_RDONLY, os.ModePerm)
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

func setCAT(cos uint, mask uint64) {
	if !catSupported {
		return
	}
	cat := C.struct_pqos_l3ca{
		class_id: C.unsigned(cos),
		cdp:      0,
	}
	C.set_l3ca_mask(&cat, C.uint64_t(mask))
	for i := C.uint(0); i < C.cat_id_count; i++ {
		if ec := C.pqos_l3ca_set(C.arr_index(C.cat_ids, i), 1, &cat); ec != C.PQOS_RETVAL_OK {
			log.Printf("pqos set cat error code %d", ec)
		}
	}
}

// return MBA real policy value
func setMBA(cos uint, percentage uint) uint {
	if !mbaSupported {
		return 0
	}
	mba := C.struct_pqos_mba{
		class_id: C.unsigned(cos),
		mb_max:   C.unsigned(percentage),
		ctrl:     0,
	}
	var mbaResult C.struct_pqos_mba
	for i := C.uint(0); i < C.mba_id_count; i++ {
		if ec := C.pqos_mba_set(C.arr_index(C.mba_ids, i), 1, &mba, &mbaResult); ec != C.PQOS_RETVAL_OK {
			log.Printf("pqos set mba error code %d", ec)
		}
	}
	return uint(mbaResult.mb_max)
}
