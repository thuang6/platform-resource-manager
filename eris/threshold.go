package main

import (
	"encoding/json"
	"io/ioutil"
	"os"
)

type BinThreshold struct {
	UtilStart float64 `json:"util_start"`
	UtilEnd   float64 `json:"util_end"`
	Cpi       float64 `json:"cpi"`
	Mpki      float64 `json:"mpki"`
	Mb        float64 `json:"mb"`
	L2spki    float64 `json:"l2spki"`
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
	LcUtilMax float64 `json:"lcutilmax"`
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

func detectTDPContention(m Metric) int {
	if *detect {
		if t, ok := thresholds.Workloads[m.Name]; ok && t.TdpThreshold != nil {
			if m.CPUUtilization >= t.TdpThreshold.Util && float64(m.NormalizedFrequency) < t.TdpThreshold.Bar {
				return tdpContention
			}
		}
	}
	return noContention
}

func detectContention(m Metric) []int {
	content := []int{}
	if *detect {
		if t, ok := thresholds.Workloads[m.Name]; ok {
			u := m.CPUUtilization
			for i := 0; i < len(t.MetricsThreshold); i++ {
				bt := t.MetricsThreshold[i]
				if (bt.UtilStart <= u && u < bt.UtilEnd) || (i == len(t.MetricsThreshold)-1 && u >= bt.UtilEnd) {
					if m.CyclesPerInstruction > bt.Cpi {
						if m.CacheMissPerKiloInstructions > bt.Mpki {
							content = append(content, llcContention)
						}
						//						if m.StallsMemoryLoadPerKiloInstructions > bt.Mspki {
						//							content = append(content, mbwContention)
						//						}
					}
					return content
				}
			}
		}
	}
	return content
}
