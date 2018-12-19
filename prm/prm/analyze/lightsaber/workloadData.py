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

""" This is the basic workload data module """

import csv


class WorkloadData(object):

    def __init__(self, filename, id):
        length = 0
        id_index = 0
        time_index = 0
        cpi_index = 0
        mpki_index = 0
        util_index = 0
        occu_index = 0
        self.time = []
        self.cpi = []
        self.mpki = []
        self.util = []
        self.occu = []
        self.contention = []

        with open(filename, 'r') as csvFile:
            reader = csv.reader(csvFile)
            for row in reader:
                if length == 0:
                    length = len(row)
                    for i in range(length):
                        if (row[i] == "name"):
                            id_index = i
                        if (row[i] == "timestamp"):
                            time_index = i
                        if (row[i] == "cycles_per_instruction"):
                            cpi_index = i
                        if (row[i] == "cache_miss_per_kilo_instruction"):
                            mpki_index = i
                        if (row[i] == "cpu_utilization"):
                            util_index = i
                        if (row[i] == "cache_occupancy"):
                            occu_index = i
                elif row[id_index] == id:
                    self.time.append(float(row[time_index]))
                    self.cpi.append(float(row[cpi_index]))
                    self.mpki.append(float(row[mpki_index]))
                    self.util.append(float(row[util_index]))
                    self.occu.append(float(row[occu_index]))
                    self.contention.append(0)
        self.get_max_util()

    def get_max_util(self):
        self.max_util = 0
        length = len(self.time)
        for i in range(length):
            if (self.max_util < self.util[i]):
                self.max_util = self.util[i]

    def get_cache_data(self, min_util, max_util):
        time = []
        mpki = []
        occu = []
        util = []
        length = len(self.time)
        for i in range(length):
            if (self.util[i] <= max_util and self.util[i] > min_util):
                time.append(self.time[i])
                mpki.append(self.mpki[i])
                occu.append(self.occu[i])
                util.append(self.util[i])
        return time, mpki, occu, util

    def get_cpi_data(self, min_util, max_util):
        time = []
        cpi = []
        contention = []
        util = []
        length = len(self.time)
        for i in range(length):
            if (self.util[i] <= max_util and self.util[i] > min_util):
                time.append(self.time[i])
                cpi.append(self.cpi[i])
                contention.append(self.contention[i])
                util.append(self.util[i])
        return time, cpi, contention, util

    def print_data(self):
        length = len(self.time)
        for i in range(length):
            output_str = str(self.time[i])
            output_str = output_str + ", " + str(self.util[i])
            output_str = output_str + ", " + str(self.cpi[i])
            output_str = output_str + ", " + str(self.mpki[i])
            output_str = output_str + ", " + str(self.occu[i])
            print(output_str)

    def label_mpki_contention(self, min_util, max_util, threshold):
        length = len(self.time)
        for i in range(length):
            if (self.util[i] <= max_util and self.util[i] > min_util and self.mpki[i] > threshold):
                self.contention[i] = 1
