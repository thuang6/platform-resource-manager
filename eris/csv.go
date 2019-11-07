package main

import (
	"fmt"
	"reflect"
	"strings"
)

func getHeaders(v interface{}) []string {
	headers := []string{}
	vType := reflect.TypeOf(v)
	for i := 0; i < vType.NumField(); i++ {
		tags := vType.Field(i).Tag
		h := tags.Get("header")
		pf := tags.Get("platform")
		if h != "" && (pf == "" || strings.Index(pf, platform) != -1) {
			headers = append(headers, h)
		}
	}
	return headers
}

func getEntry(v interface{}) []string {
	result := []string{}
	vType := reflect.TypeOf(v)
	vValue := reflect.ValueOf(v)
	for i := 0; i < vType.NumField(); i++ {
		tags := vType.Field(i).Tag
		h := tags.Get("header")
		pf := tags.Get("platform")
		if h != "" && (pf == "" || strings.Index(pf, platform) != -1) {
			s := fmt.Sprintf("%v", vValue.Field(i).Interface())
			result = append(result, s)
		}
	}
	return result
}
