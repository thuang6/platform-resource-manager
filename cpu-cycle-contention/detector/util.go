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
	"encoding/json"
	"io"
	"io/ioutil"
	"math"
)

const utilThreshold = 0.15
const zeroFilter = 1.0

type UtilizationData struct {
	Jobs  []string
	Total []float64
	Data  [][]float64
}

func NewUtilizationData(r io.Reader) (util *UtilizationData, err error) {
	var req struct {
		Jobs []string
		Data [][]float64
	}
	payload, err := ioutil.ReadAll(r)
	if err != nil {
		return
	}
	err = json.Unmarshal(payload, &req)
	if err != nil {
		return
	}

	t := make([]float64, len(req.Data[0]))
	for i := 0; i < len(req.Data[0]); i++ {
		for j := 0; j < len(req.Jobs); j++ {
			t[i] += req.Data[j][i]
		}
	}
	util = &UtilizationData{
		Jobs:  req.Jobs,
		Total: t,
		Data:  req.Data,
	}
	return
}

func (this *UtilizationData) GetContendingData(job int) (free []float64, skeptical []float64, max float64) {
	max, min := -1.0, 100000.0
	for i := 0; i < len(this.Data[job]); i++ {
		if this.Data[job][i] > max && this.Total[i]-this.Data[job][i] > zeroFilter {
			max = this.Data[job][i]
		}
		if this.Data[job][i] < min && this.Total[i]-this.Data[job][i] > zeroFilter {
			min = this.Data[job][i]
		}
	}
	low := min + (max-min)*utilThreshold
	high := max - (max-min)*utilThreshold
	free = make([]float64, 0, len(this.Total))
	skeptical = make([]float64, 0, len(this.Total))
	for i := 0; i < len(this.Total); i++ {
		delta := this.Total[i] - this.Data[job][i]
		if this.Data[job][i] <= low && delta > zeroFilter {
			free = append(free, delta)
		}
		if this.Data[job][i] >= high && delta > zeroFilter {
			skeptical = append(skeptical, delta)
		}
	}
	return
}

func (this *UtilizationData) GetCoeff() [][]float64 {
	ex := make([]float64, len(this.Jobs))
	ex2 := make([][]float64, len(this.Jobs))
	coeff := make([][]float64, len(this.Jobs))
	count := float64(len(this.Total))
	for i := 0; i < len(this.Jobs); i++ {
		ex2[i] = make([]float64, len(this.Jobs))
		coeff[i] = make([]float64, len(this.Jobs))
	}
	for i := 0; i < len(this.Total); i++ {
		for j := 0; j < len(this.Jobs); j++ {
			for k := 0; k < len(this.Jobs); k++ {
				ex2[j][k] += this.Data[j][i] * this.Data[k][i]
			}
			ex[j] += this.Data[j][i]
		}
	}
	for i := 0; i < len(this.Jobs); i++ {
		ex[i] = ex[i] / count
		for j := 0; j < len(this.Jobs); j++ {
			ex2[i][j] = ex2[i][j] / count
		}
	}
	for i := 0; i < len(this.Jobs); i++ {
		for j := 0; j < len(this.Jobs); j++ {
			coeff[i][j] = (ex2[i][j] - ex[i]*ex[j]) / math.Sqrt((ex2[i][i]-ex[i]*ex[i])*(ex2[j][j]-ex[j]*ex[j]))
		}
	}
	return coeff
}
