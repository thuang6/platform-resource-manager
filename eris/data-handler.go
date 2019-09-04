package main

import (
	"encoding/csv"
	"os"
)

var metricChannel = make(chan map[string]Metric, 2)
var utilizationChannel = make(chan []Utilization, 1000)

func initCsvHeader(csvFile string, v interface{}) *csv.Writer {
	var csvWriter *csv.Writer
	f, err := os.OpenFile(csvFile, os.O_APPEND|os.O_WRONLY, os.ModePerm)
	if err != nil {
		f, err = os.OpenFile(csvFile, os.O_CREATE|os.O_APPEND|os.O_RDWR, os.ModePerm)
		if err != nil {
			panic(err)
		}
		csvWriter = csv.NewWriter(f)
		csvWriter.Write(getHeaders(v))
		csvWriter.Flush()
	} else {
		csvWriter = csv.NewWriter(f)
	}
	return csvWriter
}

func handleData() {

	var metricCsvWriter, utilCsvWriter *csv.Writer
	if *recordMetric {
		metricCsvWriter = initCsvHeader(*metricFile, Metric{})
	}
	if *recordUtil {
		utilCsvWriter = initCsvHeader(*utilFile, Utilization{})
	}

	count := 0
	for {
		select {
		case utils := <-utilizationChannel:
			var lcUtils, beUtils float64
			ts := utils[0].Time
			for _, u := range utils {
				if *prometheusPort != 0 {
					updateMetrics(u, u.Cid, u.Name)
				}
				if *recordUtil {
					utilCsvWriter.Write(getEntry(u))
				}
				if _, ok := latencyCritical[u.Name]; ok {
					lcUtils += u.CPUUtilization
				}
				if _, ok := bestEffort[u.Name]; ok {
					beUtils += u.CPUUtilization
				}
			}
			if *recordUtil {
				ulc := Utilization{Time: ts, Cid: "", Name: "lcs", CPUUtilization: lcUtils}
				utilCsvWriter.Write(getEntry(ulc))
				if count++; count%20 == 0 {
					utilCsvWriter.Flush()
				}
			}
			if lcUtils > thresholds.LcUtilMax {
				updateLcUtilMax(lcUtils)
			}
		case metrics := <-metricChannel:
			contends := map[int]bool{llcContention: false, mbwContention: false, tdpContention: false}
			for _, m := range metrics {
				if *prometheusPort != 0 {
					updateMetrics(m, m.Cid, m.Name)
				}
				if *recordMetric {
					metricCsvWriter.Write(getEntry(m))
				}
				if *detect {
					detectContention(metrics, m, contends)
					detectTDPContention(m, contends)
				}
			}
			if *recordMetric {
				metricCsvWriter.Flush()
			}
		}
	}
}
