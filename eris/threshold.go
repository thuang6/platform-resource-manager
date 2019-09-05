package main

import (
	"encoding/json"
	"io/ioutil"
	"log"
	"os"
)

type BinThreshold struct {
	UtilStart float64 `json:"util_start"`
	UtilEnd   float64 `json:"util_end"`
	Cpi       float64 `json:"cpi"`
	Mpki      float64 `json:"mpki"`
	Mb        float64 `json:"mb"`
	Cpl3m     float64 `json:"cpl3m"`
	Mspki     float64 `json:"mspki"`
}

type WorkloadThreshold struct {
	TdpThreshold *struct {
		Util float64 `json:"util"`
		Mean float64 `json:"mean"`
		Std  float64 `json:"std"`
		Bar  float64 `json:"bar"`
	} `json:"tdp_threshold"`
	MetricsThreshold []BinThreshold `json:"metrics_threshold"`
}

type Threshold struct {
	LcUtilMax float64                      `json:"lcutilmax"`
	Workloads map[string]WorkloadThreshold `json:"workloads"`
}

var thresholds = Threshold{}

func initThreshold() {
	if *detect {
		f, err := os.OpenFile(*threshFile, os.O_RDONLY, os.ModePerm)
		if err != nil {
			panic(err)
		}
		defer f.Close()
		bs, err := ioutil.ReadAll(f)
		if err != nil {
			panic(err)
		}
		err = json.Unmarshal(bs, &thresholds)
		if err != nil {
			panic(err)
		}
	}
}

func updateLcUtilMax(lcmax float64) {
	thresholds.LcUtilMax = lcmax
	if *detect {
		thresh, err := json.Marshal(thresholds)
		if err != nil {
			panic(err)
		}
		err = ioutil.WriteFile(*threshFile, thresh, os.ModePerm)
		if err != nil {
			panic(err)
		}
	}
}

func detectTDPContention(m Metric, cm map[int]bool) {
	if t, ok := thresholds.Workloads[m.Name]; ok && t.TdpThreshold != nil {
		if m.CPUUtilization >= t.TdpThreshold.Util && float64(m.NormalizedFrequency) < t.TdpThreshold.Bar {
			cm[tdpContention] = true
			log.Printf("TDP Contention ! Workload: %s, CPU Usage: %+v, Frequency: %+v, Thresh: %+v, Bar: %+v\n",
				m.Name, m.CPUUtilization, m.NormalizedFrequency, t.TdpThreshold.Util, t.TdpThreshold.Bar)
		}
	}
}

func detectContender(metrics map[string]Metric, id string, ct int) {
	suspect := "unknown"
	maxValue := 0.0
	for n, m := range metrics {
		var val float64
		if n != id {
			if ct == llcContention {
				val = float64(m.CacheOccupancy)
			} else if ct == mbwContention {
				val = m.MemoryBandwidthTotal
			}
			if val > maxValue {
				maxValue = val
				suspect = n
			}
		}
	}
	log.Printf("Suspect Contender: %s\n", suspect)
}

func detectInBin(bt BinThreshold, m Metric, metrics map[string]Metric, cm map[int]bool) {
	if m.CyclesPerInstruction > bt.Cpi {
		unknown := true
		if m.CacheMissPerKiloInstructions > bt.Mpki {
			cm[llcContention] = true
			unknown = false
			log.Printf("LLC Contention ! Workload: %s, CPU Usage: %+v, CPI: %+v, Thresh: %+v, MPKI: %+v, Thresh: %+v\n",
				m.Name, m.CPUUtilization, m.CyclesPerInstruction, bt.Cpi, m.CacheMissPerKiloInstructions, bt.Mpki)
			detectContender(metrics, m.Name, llcContention)
		}
		if m.CyclesPerL3Miss > bt.Cpl3m {
			cm[mbwContention] = true
			unknown = false
			log.Printf("MB Contention ! Workload %s, CPU Usage: %+v, CPI: %+v, Thresh: %+v, CPL3M: %+v, Thresh: %+v\n",
				m.Name, m.CPUUtilization, m.CyclesPerInstruction, bt.Cpi, m.CyclesPerL3Miss, bt.Cpl3m)
			detectContender(metrics, m.Name, mbwContention)
		}

		if unknown {
			log.Printf("Unknown Contention ! Workload %s, CPU Usage: %+v, CPI: %+v, Thresh: %+v\n",
				m.Name, m.CPUUtilization, m.CyclesPerInstruction, bt.Cpi)
		}
	}
}

func detectContention(metrics map[string]Metric, m Metric, cm map[int]bool) {
	if t, ok := thresholds.Workloads[m.Name]; ok {
		u := m.CPUUtilization
		for i := 0; i < len(t.MetricsThreshold); i++ {
			bt := t.MetricsThreshold[i]
			if u < bt.UtilStart {
				if i == 0 {
					return
				}
				detectInBin(t.MetricsThreshold[i-1], m, metrics, cm)
				return
			}
			if u <= bt.UtilEnd || i == len(t.MetricsThreshold)-1 {
				detectInBin(bt, m, metrics, cm)
				return
			}
		}
	}
}
