package main

import (
	"encoding/csv"
	"log"
	"os"
)

var metricChannel = make(chan *Metric, 1000)
var utilizationChannel = make(chan *Utilization, 1000)

func handleData() {

	var metricCsvWriter, utilCsvWriter *csv.Writer
	if *record {
		f, err := os.OpenFile(*metricFile, os.O_APPEND|os.O_WRONLY, os.ModePerm)
		if err != nil {
			f, err = os.OpenFile(*metricFile, os.O_CREATE|os.O_APPEND|os.O_RDWR, os.ModePerm)
			if err != nil {
				panic(err)
			}
			metricCsvWriter = csv.NewWriter(f)
			metricCsvWriter.Write(getHeaders(Metric{}))
			metricCsvWriter.Flush()
		} else {
			metricCsvWriter = csv.NewWriter(f)
		}
		f, err = os.OpenFile(*utilFile, os.O_APPEND|os.O_WRONLY, os.ModePerm)
		if err != nil {
			f, err = os.OpenFile(*utilFile, os.O_CREATE|os.O_APPEND|os.O_RDWR, os.ModePerm)
			if err != nil {
				panic(err)
			}
			utilCsvWriter = csv.NewWriter(f)
			utilCsvWriter.Write(getHeaders(Utilization{}))
			utilCsvWriter.Flush()
		} else {
			utilCsvWriter = csv.NewWriter(f)
		}
	}

	for {
		select {
		case m := <-metricChannel:
			if *prometheusPort != 0 {
				updateMetrics(*m)
			}
			if *record {
				metricCsvWriter.Write(getEntry(*m))
				metricCsvWriter.Flush()
			}
			if *detect {
				c := detectContention(*m)
				tdpc := detectTDPContention(*m)
				c = append(c, tdpc)
				for i := 0; i < len(c); i++ {
					switch c[i] {
					case tdpContention:
						log.Printf("TDP Contention! NF: %+v", m.NormalizedFrequency)
					case llcContention:
						log.Printf("LLC Contention! NF: %+v", m.CacheMissPerKiloInstructions)
					case mbwContention:
						//						log.Printf("MBW Contention! MSPKI: %+v", m.StallsMemoryLoadPerKiloInstructions)
					}
				}
			}
		}
	}
}
