package main

var utilizationHeaders = []string{}

type Utilization struct {
	Time           uint64  `header:"time"`
	Cid            string  `header:"cid"`
	Name           string  `header:"name"`
	CPUUtilization float64 `header:"cpu_utilization"`
}

func startCollectUtilization() {

}
