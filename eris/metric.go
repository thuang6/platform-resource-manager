package main

import (
	"log"
	"reflect"
	"runtime"
	"strings"
	"time"
)

var eventIndex = map[string]int{}

type Metric struct {
	Time                         uint64  `header:"time"`
	Cid                          string  `header:"cid"`
	Name                         string  `header:"name"`
	Instruction                  uint64  `header:"instruction" event:"INST_RETIRED.ANY_P" gauge:"cma_instructions" gauge_help:"Instructions of a container"`
	Cycle                        uint64  `header:"cycle" event:"CPU_CLK_UNHALTED.THREAD_P" gauge:"cma_unhalted_cycles" gauge_help:"Unhalted cycles of a container"`
	CyclesPerInstruction         float64 `header:"cycles_per_instruction" gauge:"cma_cycles_per_instruction" gauge_help:" Cycles per instruction of a container"`
	CacheMissPerKiloInstructions float64 `header:"cache_miss_per_kilo_instruction" gauge:"cma_misses_per_kilo_instruction" gauge_help:"Misses per kilo instruction of a container"`
	CacheMiss                    uint64  `header:"cache_miss" event:"LONGEST_LAT_CACHE.MISS" gauge:"cma_llc_miss" gauge_help:"Cache misses of a container"`
	NormalizedFrequency          uint64  `header:"normalized_frequency" gauge:"cma_average_frequency" gauge_help:"Normalized Frequency of a container"`
	CPUUtilization               float64 `header:"cpu_utilization" gauge:"cma_cpu_usage_percentage" gauge_help:"CPU usage percentage of a container"`
	CacheOccupancy               uint64  `header:"cache_occupancy" gauge:"cma_llc_occupancy" gauge_help:"Last level cache occupancy of a container"`
	MemoryBandwidthLocal         float64 `header:"memory_bandwidth_local"`
	MemoryBandwidthRemote        float64 `header:"memory_bandwidth_remote"`
	MemoryBandwidthTotal         float64 `gauge:"cma_memory_bandwidth" gauge_help:"Total memory bandwidth of a container"`
	//	StallsL2Miss                        uint64  `header:"stalls_l2_miss" event:"CYCLE_ACTIVITY.STALLS_L2_MISS"`
	//	StallsMemoryLoad                    uint64  `header:"stalls_mem_load" event:"CYCLE_ACTIVITY.STALLS_MEM_ANY"`
	//	StallsL2MissPerKiloInstructions     float64 `header:"stalls_l2miss_per_kilo_instruction"`
	//	StallsMemoryLoadPerKiloInstructions float64 `header:"stalls_memory_load_per_kilo_instruction" gauge:"cma_stalls_mem_per_instruction" gauge_help:"Stalls memory load per instruction of a container"`
	L3MissRequests  uint64  `header:"l3_miss_requests" event:"OFFCORE_REQUESTS.L3_MISS_DEMAND_DATA_RD" gauge:"cma_l3miss_requests" gauge_help:"l3 miss requests count"`
	L3MissCycles    uint64  `header:"l3_miss_cycles" event:"OFFCORE_REQUESTS_OUTSTANDING.L3_MISS_DEMAND_DATA_RD" gauge:"cma_l3miss_cycles" gauge_help:"l3 miss cycle count"`
	CyclesPerL3Miss float64 `header:"cycles_per_l3_miss" gauge:"cma_cycles_per_l3_miss" gauge_help:"cycles per l3 miss"`
	//PMMInstruction         uint64  `header:"pmm_instruction" event:"MEM_LOAD_RETIRED.LOCAL_PMM" gauge:"cma_pmm_instruction" gauge_help:"instruction retired for pmm"`
}

func init() {
	m := Metric{}
	mType := reflect.TypeOf(m)
	for i := 0; i < mType.NumField(); i++ {
		tags := mType.Field(i).Tag
		e := tags.Get("event")
		if e != "" {
			eventIndex[e] = i
		}
	}
}

var containers = map[string]*Container{}

func updateContainers() {
	cons, err := getContainers()
	if err != nil {
		log.Println(err)
	} else {
		for id, container := range containers {
			// remove all finished containers
			if _, ok := cons[id]; err == nil && !ok {
				container.finalize()
				delete(containers, id)
			}
		}

		for id, name := range cons {
			// initialize new containers
			if _, ok := containers[id]; !ok {
				cgroup, err := newContainer(id, strings.TrimLeft(name, "/"))
				if err != nil {
					//							log.Println(err)
				} else {
					containers[id] = cgroup
				}
			}
		}
	}
}

func startCollectMetrics() {
	ticker := newDelayedTicker(0, time.Duration(*metricInterval)*time.Second)
	utilTicker := newDelayedTicker(0, time.Duration(*utilInterval)*time.Second)
	pqosUpdate := time.NewTicker(time.Duration(1 * time.Second))
	for {
		select {
		case <-pqosUpdate.C:
			for _, c := range containers {
				pidsMap, err := listTaskPid(c.id)
				if err != nil {
					continue
				} else {
					err := updatePqosGroup(c.pqosMonitorData, c.pqosPidsMap, pidsMap)
					if err != nil {
						log.Println(err)
					}
					c.pqosPidsMap = pidsMap
				}

			}
		case <-utilTicker.C:
			updateContainers()
			ts := uint64(time.Now().Unix())
			var utils []Utilization
			for id, container := range containers {
				u := Utilization{Time: ts, Cid: id, Name: container.name}
				cpuData := container.pollCPUUsage(false)
				if cpuData != nil && cpuData[1] != 0 {
					u.CPUUtilization = float64(cpuData[0]) / float64(cpuData[1]) * float64(runtime.NumCPU()) * 100.0
					utils = append(utils, u)
				}
			}
			if len(utils) > 0 {
				utilizationChannel <- utils
			}
		case <-ticker.C:
			updateContainers()
			ts := uint64(time.Now().Unix())
			metrics := map[string]Metric{}
			for id, container := range containers {
				if !container.monitorStarted {
					container.start()
					container.monitorStarted = true
					continue
				}

				m := Metric{Time: ts, Cid: id, Name: container.name}
				// read perf data
				perfData := container.pollPerf()
				if perfData != nil {
					for i := 0; i < len(peCounters); i++ {
						m.setEventMetric(peCounters[i].EventName, perfData[i])
					}
				}
				// read cpu utilization data
				cpuData := container.pollCPUUsage(true)
				if cpuData != nil && cpuData[1] != 0 {
					m.CPUUtilization = float64(cpuData[0]) / float64(cpuData[1]) * float64(runtime.NumCPU()) * 100.0
				}

				// read pqos rdt data
				pqosData := container.pollPqos()
				if pqosData != nil {
					m.CacheOccupancy = pqosData[0] / 1024
					m.MemoryBandwidthLocal = float64(pqosData[1]) / 1024.0 / 1024.0 / float64(*metricInterval)
					m.MemoryBandwidthRemote = float64(pqosData[2]) / 1024.0 / 1024.0 / float64(*metricInterval)
				}

				m.calculate()
				if perfData != nil && cpuData != nil && pqosData != nil {
					metrics[container.name] = m
				}
			}
			if len(metrics) > 0 {
				metricChannel <- metrics
			}
		}
	}
}

func (m *Metric) setEventMetric(event string, value uint64) {
	index, ok := eventIndex[event]
	if !ok {
		panic("trying to set a not predefined value")
	}
	mPtr := reflect.ValueOf(m)
	mPtr.Elem().Field(index).SetUint(value)
}

func (m *Metric) calculate() {
	if m.Instruction != 0 {
		m.CyclesPerInstruction = float64(m.Cycle) / float64(m.Instruction)
		m.CacheMissPerKiloInstructions = float64(m.CacheMiss) / float64(m.Instruction) * 1000.0
		//		m.StallsL2MissPerKiloInstructions = float64(m.StallsL2Miss) / float64(m.Instruction) * 1000
		//		m.StallsMemoryLoadPerKiloInstructions = float64(m.StallsMemoryLoad) / float64(m.Instruction) * 1000
	}
	if m.CPUUtilization != 0 {
		m.NormalizedFrequency = uint64(float64(m.Cycle) / float64(*metricInterval) / 10000.0 / m.CPUUtilization)
	}
	if m.L3MissRequests != 0 {
		m.CyclesPerL3Miss = float64(m.L3MissCycles) / float64(m.L3MissRequests)
	}
	m.MemoryBandwidthTotal = m.MemoryBandwidthLocal + m.MemoryBandwidthRemote
}
