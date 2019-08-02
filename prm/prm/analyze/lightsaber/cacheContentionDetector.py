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

""" This module implements the cache contention detector taking a noisy history as the input """

import cacheAnalyzer
import cpiAnalyzer
import configConstants


class CacheContentionDetector(object):
    def __init__(self, data):
        self.bin_util_thresolds = []
        self.mpki_thresholds = []
        self.cpi_thresholds = []

        util_threshold = data.max_util
        bin_step = configConstants.ConfigConstants.step
        if (configConstants.ConfigConstants.use_ratio):
            if (bin_step < data.max_util * configConstants.ConfigConstants.step_ratio):
                bin_step = data.max_util * configConstants.ConfigConstants.step_ratio

        tmp_util = util_threshold
        while (util_threshold > data.max_util * configConstants.ConfigConstants.lower_util_bound):
            util_threshold -= bin_step
            time, mpki, occu, _ = data.get_cache_data(util_threshold, tmp_util)
            if (len(time) < configConstants.ConfigConstants.min_data_points):
                continue
            output_str = "Bin: " + str(util_threshold)
            print(output_str)
            self.bin_util_thresolds.append(util_threshold)
            analyzer = cacheAnalyzer.CacheAnalyzer(time, mpki, occu)
            mpki_threshold, occu_threshold = analyzer.analyze()
            self.mpki_thresholds.append(mpki_threshold)
            output_str = "Final MPKI threshold: " + \
                str(mpki_threshold) + ", LLC occupancy threshold: " + str(occu_threshold)
            print(output_str)
            data.label_mpki_contention(util_threshold, tmp_util, mpki_threshold)
            time, cpi, contention, _ = data.get_cpi_data(util_threshold, tmp_util)
            analyzer = cpiAnalyzer.CPIAnalyzer(time, cpi, contention)
            cpi_threshold = analyzer.analyze()
            output_str = "Final CPI threshold: " + str(cpi_threshold)
            print(output_str)
            print()
            self.cpi_thresholds.append(cpi_threshold)
            tmp_util = util_threshold

    def detect(self, util, cpi, mpki):
        length = len(self.bin_util_thresolds)
        for i in range(length):
            if (util > self.bin_util_thresolds[i]):
                if (cpi > self.cpi_thresholds[i] and mpki > self.mpki_thresholds[i]):
                    return True
        return False
