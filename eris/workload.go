package main

import (
	"encoding/json"
	"io/ioutil"
	"os"
)

type workload struct {
	CPU  int    `json:"cpus"`
	Type string `json:"type"`
}

var workloadMeta = map[string]workload{}
var latencyCritical = map[string]workload{}
var bestEffort = map[string]workload{}

func initWorkload() {
	f, err := os.Open(*workloadConfFile)
	if err != nil {
		panic(err)
	}
	defer f.Close()
	b, err := ioutil.ReadAll(f)
	if err != nil {
		panic(err)
	}
	json.Unmarshal(b, &workloadMeta)
	for k, v := range workloadMeta {
		if v.Type == "best_efforts" {
			bestEffort[k] = v
		} else {
			latencyCritical[k] = v
		}
	}
}
