package main

import "time"

type delayedTicker struct {
	C chan bool
}

func newDelayedTicker(delay, period time.Duration) *delayedTicker {
	ret := &delayedTicker{C: make(chan bool, 1)}
	time.Sleep(delay)
	go func() {
		tick := time.NewTicker(period)
		for ; ; <-tick.C {
			ret.C <- true
		}
	}()
	return ret
}
