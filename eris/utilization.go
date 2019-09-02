package main

var utilizationHeaders = []string{}

type Utilization struct {
	Time           uint64  `header:"time"`
	Cid            string  `header:"cid"`
	Name           string  `header:"name"`
	CPUUtilization float64 `header:"cpu_utilization" gauge:"cma_cpu_usage_percentage_1" gauge_help:"CPU usage percentage of a container in small granularity"`
}

func startCollectUtilization() {

}
