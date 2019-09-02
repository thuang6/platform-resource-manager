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

func prometheusStart(vs []interface{}) {
	for _, v := range vs {
		vType := reflect.TypeOf(v)
		for i := 0; i < vType.NumField(); i++ {
			tags := vType.Field(i).Tag
			g, gh := tags.Get("gauge"), tags.Get("gauge_help")
			if g != "" && gh != "" {
				gauges[g] = prometheus.NewGaugeVec(prometheus.GaugeOpts{
					Name: g,
					Help: gh,
				}, []string{"container", "name"})
				registry.MustRegister(gauges[g])
			}
		}
	}

	http.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{}))
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", *prometheusPort), nil))
}

func updateMetrics(v interface{}, cid, name string) {
	vType := reflect.TypeOf(v)
	vValue := reflect.ValueOf(v)
	for i := 0; i < vType.NumField(); i++ {
		tags := vType.Field(i).Tag
		g, gh := tags.Get("gauge"), tags.Get("gauge_help")
		if g != "" && gh != "" {
			gaugeVec := gauges[g]
			metric, err := gaugeVec.GetMetricWithLabelValues(cid, name)
			if err != nil {
				log.Println(err)
				continue
			}
			vi := vValue.Field(i).Interface()
			switch v := vi.(type) {
			case uint64:
				metric.Set(float64(v))
			case float64:
				metric.Set(float64(v))
			}
		}
	}
}
