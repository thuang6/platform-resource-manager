// Copyright (C) 2018 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions
// and limitations under the License.
//
//
// SPDX-License-Identifier: Apache-2.0

package handler

import (
	"io/ioutil"
	"log"
	"net/http"
	"os"
)

var indexTemplate []byte

func init() {
	f, err := os.OpenFile("template/index.html", os.O_RDONLY, os.ModePerm)
	if err != nil {
		log.Fatal(err)
		return
	}
	defer f.Close()
	indexTemplate, err = ioutil.ReadAll(f)
	if err != nil {
		log.Fatal(err)
		return
	}
}

type IndexHandler struct {
}

func (this *IndexHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Add("content-type", "text/html")
	_, err := w.Write(indexTemplate)
	if err != nil {
		log.Println(err.Error())
		return
	}
}
