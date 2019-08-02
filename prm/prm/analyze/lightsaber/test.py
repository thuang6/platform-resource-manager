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

""" This shows an example of using the cache contention detector
to detect cache contentions in a noisy history """

import sys
import datetime
import workloadData
import cacheContentionDetector
import configConstants

if __name__ == '__main__':
    workload_filename = "workload-data-big-clean.csv"
    workload_name = "twemcache--11211"

    if len(sys.argv) > 2:
        workload_filename = sys.argv[1]
        workload_name = sys.argv[2]

    data = workloadData.WorkloadData(workload_filename, workload_name)
    detector = cacheContentionDetector.CacheContentionDetector(data)

    time, mpki, occu, util = data.get_cache_data(0, data.max_util)
    time, cpi, contention, util = data.get_cpi_data(0, data.max_util)

    if (configConstants.ConfigConstants.verbose > 2):
        print("Timestamp, CPI, Potential contention, MPKI, LLC occupancy, Utilization")
        for i in range(len(time)):
            datatime_human_str = datetime.datetime.fromtimestamp(
                time[i]).strftime('%Y-%m-%d %H:%M:%S')
            output_str = str(datatime_human_str) + ", " + str(cpi[i]) + ", " + str(
                contention[i]) + ", " + str(mpki[i]) + ", " + str(occu[i]) + ", " + str(util[i])
            # output_str = str(time[i]) + ",
            # " + str(cpi[i]) + ", " + str(contention[i]) + "," +
            # str(mpki[i]) + ", " + str(occu[i]) + ", " + str(util[i])
            print(output_str)
        print("")

    for i in range(len(time)):
        if (detector.detect(util[i], cpi[i], mpki[i])):
            datatime_human_str = datetime.datetime.fromtimestamp(
                time[i]).strftime('%Y-%m-%d %H:%M:%S')
            output_str = "LLC contention @ " + str(datatime_human_str) + ", CPI: " + str(
                cpi[i]) + ", MPKI: " + str(mpki[i]) + ", utilization: " + str(util[i])
            print(output_str)
