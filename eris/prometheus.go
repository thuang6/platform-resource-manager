package main

import (
	"fmt"
	"log"
	"net/http"
	"reflect"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var registry = prometheus.NewRegistry()
var gauges = map[string]*prometheus.GaugeVec{}

func prometheusStart() {

	m := Metric{}
	mType := reflect.TypeOf(m)
	for i := 0; i < mType.NumField(); i++ {
		tags := mType.Field(i).Tag
		g, gh := tags.Get("gauge"), tags.Get("gauge_help")
		if g != "" && gh != "" {
			gauges[g] = prometheus.NewGaugeVec(prometheus.GaugeOpts{
				Name: g,
				Help: gh,
			}, []string{"container", "name"})
			registry.MustRegister(gauges[g])
		}
	}
	http.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{}))
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", *prometheusPort), nil))
}

func updateMetrics(m Metric) {
	mType := reflect.TypeOf(m)
	mValue := reflect.ValueOf(m)
	for i := 0; i < mType.NumField(); i++ {
		tags := mType.Field(i).Tag
		g, gh := tags.Get("gauge"), tags.Get("gauge_help")
		if g != "" && gh != "" {

			gaugeVec := gauges[g]
			metric, err := gaugeVec.GetMetricWithLabelValues(m.Cid, m.Name)
			if err != nil {
				log.Println(err)
				continue
			}

			vi := mValue.Field(i).Interface()
			switch v := vi.(type) {
			case uint64:
				metric.Set(float64(v))
			case float64:
				metric.Set(float64(v))
			}
		}
	}
}
