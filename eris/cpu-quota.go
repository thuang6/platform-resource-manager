package main

import (
	"io/ioutil"
	"log"
	"os"
	"strconv"
	"strings"
)

const (
	quotaDefault = -1
	quotaMin     = 1000
	quotaCore    = 100000
	quotaPercent = quotaCore / 100
	shareBe      = 2
	shareLc      = 200000
)

type CpuQuota struct {
	AbsResource
	cpuQuota       int
	quotaMax       int
	quotaStep      int
	minMarginRatio float64
}

func (q *CpuQuota) updateSysMaxUtil(sysMaxUtil float64) {
	q.quotaMax = int(sysMaxUtil * quotaPercent)
	q.quotaStep = q.quotaMax / resLevMax
}

func (q *CpuQuota) update() {
	if q.isFullLevel() {
		q.cpuQuota = quotaDefault
	} else if q.isMinLevel() {
		q.cpuQuota = quotaMin
	} else {
		q.cpuQuota = q.level * q.quotaStep
	}
}

func getCfsPeriod(id string) int {
	path := getCgroupCfsPeriodPath(id)
	f, err := os.OpenFile(path, os.O_RDONLY, 0644)
	if err != nil {
		log.Println(err)
		return 0
	}
	defer f.Close()
	bs, err := ioutil.ReadAll(f)
	if err != nil {
		log.Println(err)
		return 0
	}
	s := string(bs)
	p, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		log.Println(err)
		return 0
	}
	return p
}

func setQuota(c *Container, q int) {
	p := getCfsPeriod(c.id)
	rq := q
	if p != 0 && q != quotaDefault && q != quotaMin {
		rq = int(q * p / quotaCore)
	}
	rqs := strconv.Itoa(rq)
	path := getCgroupCfsQuotaPath(c.id)
	bs := []byte(rqs)

	err := ioutil.WriteFile(path, bs, 0644)
	if err != nil {
		log.Println(err)
		return
	}
	log.Printf("set container %s cpu quota to %+v", c.name, rq)
}

func setShare(c *Container, s int) {
	ss := strconv.Itoa(s)
	bs := []byte(ss)
	path := getCgroupSharePath(c.id)

	err := ioutil.WriteFile(path, bs, 0644)
	if err != nil {
		log.Println(err)
		return
	}
	log.Printf("set container %s cpu share to %+v", c.id, s)
}

func (q *CpuQuota) budgeting(bes []*Container, lcs []*Container) {
	q.update()

	newq := int(q.cpuQuota / len(bes))
	for _, c := range bes {
		if q.isMinLevel() || q.isFullLevel() {
			setQuota(c, q.cpuQuota)
		} else {
			setQuota(c, newq)
		}
	}
}

func (q *CpuQuota) detectMarginExceed(lcUtils float64, beUtils float64) (bool, bool) {
	beq := q.cpuQuota
	margin := quotaCore * q.minMarginRatio

	if *verbose {
		log.Printf("lcUtils: %+v, beUtils: %+v, beq: %+v, margin: %+v",
			lcUtils, beUtils, beq, margin)
	}
	exceed := lcUtils == 0 || (lcUtils+beUtils)*quotaPercent+margin > float64(q.quotaMax)
	hold := (lcUtils+beUtils)*quotaPercent+margin >= float64(q.quotaMax-q.quotaStep)
	return exceed, hold
}
