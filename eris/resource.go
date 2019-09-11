package main

const (
	resLevFull = -1
	resLevMin  = 0
	resLevMax  = 20
)

type Resource interface {
	isMinLevel() bool
	isFullLevel() bool
	setLevel(level int)
	increaseLevel()
	budgeting(bes []*Container, lcs []*Container)
}

type AbsResource struct {
	level    int
	levelMax int
}

func (r *AbsResource) isMinLevel() bool {
	return r.level == resLevMin
}

func (r *AbsResource) isFullLevel() bool {
	return r.level == resLevFull
}

func (r *AbsResource) setLevel(level int) {
	r.level = level
}

func (r *AbsResource) increaseLevel() {
	r.level++
	if r.level == r.levelMax {
		r.level = resLevFull
	}
}
