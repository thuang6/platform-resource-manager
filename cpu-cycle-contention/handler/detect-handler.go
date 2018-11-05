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
	"encoding/json"
	"log"
	"net/http"

	"github.com/intel/platform-resource-manager/cpu-cycle-contention/detector"
)

type DetectHandler struct {
}

func (this *DetectHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	obj, err := detector.Detect("CDF", r.Body)
	if err != nil {
		log.Println(err.Error())
		return
	}
	res, err := json.Marshal(obj)
	if err != nil {
		log.Println(err.Error())
		return
	}
	w.Write(res)
}
