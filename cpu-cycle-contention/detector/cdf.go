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
	"math"
	"sort"
)

const probStep = 0.02
const checkpoints = 10
const threshold = 0.2

func getPercentileValue(data []float64, percentile float64) float64 {
	index := int(float64(len(data))*percentile) - 1
	if index < 0 {
		return data[0]
	} else {
		return data[index]
	}
}

func CDFDetect(free, skeptical []float64, contendingUtilization float64) bool {
	sort.Float64s(free)
	sort.Float64s(skeptical)

	var lowDiff, highDiff float64
	for i := 0; i < checkpoints; i++ {
		p := float64(i+1) * probStep
		valueFree, valueSkeptical := getPercentileValue(free, p), getPercentileValue(skeptical, p)
		lowDiff += math.Abs(valueFree - valueSkeptical)
		p = 1.0 - float64(i+1)*probStep
		valueFree, valueSkeptical = getPercentileValue(free, p), getPercentileValue(skeptical, p)
		highDiff += (valueFree - valueSkeptical)
	}
	return (highDiff - lowDiff) > contendingUtilization*threshold*checkpoints
}
