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

package detector

import (
	"fmt"
	"io"
	"log"
)

const minDataPoint = 15

func Detect(method string, r io.Reader) (interface{}, error) {
	u, err := NewUtilizationData(r)
	if err != nil {
		log.Println(err.Error())
		return nil, err
	}
	result := []string{}
	contender := []string{}
	cdf := make([][][]interface{}, len(u.Jobs))
	free, skeptical := make([][]float64, len(u.Jobs)), make([][]float64, len(u.Jobs))
	var contendingUtilization float64

	coeff := u.GetCoeff()
	for i := 0; i < len(u.Jobs); i++ {
		contender = append(contender, "")
		min := 0.0
		for j := 0; j < len(u.Jobs); j++ {
			if min > coeff[i][j] {
				min = coeff[i][j]
				contender[i] = fmt.Sprintf("%s is contending %s. Correlation coefficient %f.", u.Jobs[j], u.Jobs[i], min)
			}
		}
	}

	switch method {
	case "CDF":
		for i := 0; i < len(u.Jobs); i++ {
			free[i], skeptical[i], contendingUtilization = u.GetContendingData(i)
			cdf[i] = make([][]interface{}, 0, 500)
			if len(free[i]) < minDataPoint || len(skeptical[i]) < minDataPoint {
				result = append(result, "not enough data")
				continue
			}
			if CDFDetect(free[i], skeptical[i], contendingUtilization) {
				result = append(result, fmt.Sprintf("%s is contending the rest.", u.Jobs[i]))
			} else {
				result = append(result, fmt.Sprintf("%s is not contending the rest. %s", u.Jobs[i], contender[i]))
			}
			for p := 0.0; p <= 1.0; p += 0.02 {
				cdf[i] = append(cdf[i], []interface{}{getPercentileValue(free[i], p), p, nil})
			}
			for p := 0.0; p <= 1.0; p += 0.02 {
				cdf[i] = append(cdf[i], []interface{}{getPercentileValue(skeptical[i], p), nil, p})
			}
		}
		return struct {
			Result          []string
			Contender       []string
			Free, Skeptical [][]float64
			CDF             [][][]interface{}
		}{result, contender, free, skeptical, cdf}, nil
	}
	return nil, nil
}
