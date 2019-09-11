package main

type Controller interface {
	update(bes []*Container, lcs []*Container, detected bool, hold bool)
}

var cpuq CpuQuota
var controllers = map[int]Controller{}

func initController() {
	cpuq = CpuQuota{AbsResource: AbsResource{level: resLevMin, levelMax: resLevMax}}
	cpuq.updateSysMaxUtil(thresholds.LcUtilMax)
	quotaController := NaiveController{res: &cpuq, cycCnt: 0, cycThresh: *quotaCycles}

	controllers[cycleContention] = &quotaController
}
