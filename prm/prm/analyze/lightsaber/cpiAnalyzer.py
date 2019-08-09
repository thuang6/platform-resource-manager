# Copyright (C) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.
#
#
# SPDX-License-Identifier: Apache-2.0

""" This module implements the process to learn the CPI anomaly threshold in a noisy history """

import numpy as np
import configConstants
import scoring
import gmmWrapper


class CPIAnalyzer(object):

    def __init__(self, time, cpi, contention):
        self.time = time
        self.cpi = cpi
        self.contention = contention
        self.gmm = None

    def analyze(self):
        self.fit_gmm()
        return self.discriminate()

    def fit_gmm(self, max_components=configConstants.ConfigConstants.max_components):
        data = []

        length = len(self.time)
        for i in range(length):
            tmp_vector = []
            tmp_vector.append(self.cpi[i])
            data.append(tmp_vector)
        data = np.array(data)

        self.gmm = gmmWrapper.GMMWrapper.fit_gmm(data)

    def discriminate(self):
        components = self.gmm.components
        thresholds = []
        indices = []
        for i in range(components):
            thresholds.append(self.gmm.get_threshold(i))
            indices.append(i)

        best_score = 0
        best_threshold = 0

        tmp_label = []
        for i in range(len(self.gmm.label)):
            tmp_label.append(0)
        for i in range(components):
            index = i
            for j in range(i, components):
                if (thresholds[indices[index]] > thresholds[indices[j]]):
                    index = j
            tmp_index = indices[i]
            indices[i] = indices[index]
            indices[index] = tmp_index
            for j in range(len(self.cpi)):
                if (self.cpi[j] > thresholds[indices[i]]):
                    tmp_label[j] = 1
                else:
                    tmp_label[j] = 0
            if (configConstants.ConfigConstants.verbose > 6):
                output_str = "  CPI threshold: " + str(thresholds[indices[i]])
                print(output_str)
            score = self.evaluate(tmp_label, self.contention)
            if (best_score < score):
                best_score = score
                best_threshold = thresholds[indices[i]]
            if (best_score == 0 and i == components - 1):
                best_threshold = thresholds[indices[i]]
        return best_threshold

    def evaluate(self, tmp_label, contention):
        total = len(tmp_label)
        positive = 0
        for i in range(total):
            if (tmp_label[i] == 1):
                positive += 1
        sub_total = total
        sub_positive = positive
        for i in range(total):
            if (contention[i] == 0):
                sub_total -= 1
                if (tmp_label[i] == 1):
                    sub_positive -= 1
        return scoring.Scoring.score(total, positive, sub_total, sub_positive)
