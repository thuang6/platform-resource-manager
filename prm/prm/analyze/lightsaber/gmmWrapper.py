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

""" This module wraps the Gaussian mixture model from sklearn library """

from sklearn import mixture
import configConstants
import math


class GMMWrapper(object):

    def __init__(self, data, max_components=configConstants.ConfigConstants.max_components):
        self.data = data
        self.gmm = None
        self.label = []
        self.fit(max_components)
        self.components = len(self.gmm.means_)
        self.labelData()

    def fit(self, max_components=configConstants.ConfigConstants.max_components):
        best_gmm = None
        bic = []
        lowest_bic = 100000000000
        for components in range(1, max_components):
            gmm = mixture.GaussianMixture(n_components=components,
                                          random_state=configConstants.ConfigConstants.rand_seed)
            gmm.fit(self.data)
            bic.append(gmm.bic(self.data))
            if bic[-1] < lowest_bic:
                lowest_bic = bic[-1]
                best_gmm = gmm
                if (configConstants.ConfigConstants.verbose > 7):
                    print("GMM fitting")
                    output_str = str(components) + ": " + str(lowest_bic) + ", " + str(best_gmm)
                    print(output_str)
        self.gmm = best_gmm
        if (configConstants.ConfigConstants.verbose > 4):
            print("GMM Data")
            for i in range(len(self.gmm.means_)):
                mean = self.gmm.means_[i][0]
                stdev = math.sqrt(self.gmm.covariances_[i][0])
                weight = self.gmm.weights_[i]
                output_str = "  Component " + str(i) + ": " + \
                    str(weight) + ", " + str(mean) + ", " + str(stdev)
                print(output_str)
            print()

    def labelData(self):
        result = self.gmm.predict_proba(self.data)
        for i in range(len(result)):
            self.label.append(0)
            p = 0
            for j in range(len(result[i])):
                if (p < result[i][j]):
                    p = result[i][j]
                    self.label[i] = j

    def get_threshold(self, i, check_strict=configConstants.ConfigConstants.check_strict):
        mean = self.gmm.means_[i][0]
        stdev = math.sqrt(self.gmm.covariances_[i][0])
        threshold = mean + stdev * configConstants.ConfigConstants.outlier_span
        if (check_strict):
            max = 0
            for j in range(len(self.label)):
                if (self.label[j] == i and max < self.data[j]):
                    max = self.data[j]
            if (max < threshold):
                threshold = max
        return threshold

    @staticmethod
    def fit_gmm(data, max_components=configConstants.ConfigConstants.max_components):
        return GMMWrapper(data, max_components)
