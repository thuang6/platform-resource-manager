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

""" This module implements platform metrics data analysis. """

import time
import copy
import logging
import json
import csv
import pandas as pd
from scipy import stats
from prm.analyze import thresh
from prm.container import Metric


log = logging.getLogger(__name__)

COLLECT_MODE = 'collect'
DETECT_MODE = 'detect'
UTIL_FILE = 'lc-util.csv'


class Analyzer:
    mode = 0
    workload_meta = {}
    workload_data = {}
    threshold = {}
    datafile = {}
    datawriter = {}
    count = 0
    col = ["name", "application", "timestamp", Metric.CYC, Metric.INST,
           Metric.L3MISS, Metric.L3OCC, Metric.MB, Metric.CPI,
           Metric.L3MPKI, Metric.NF, Metric.UTIL]

    def __init__(self):
        try:
            with open('workload-meta.json', 'r') as f:
                self.workload_meta = json.loads(f.read())
        except OSError:
            log.debug('cannot open workload-meta.json for reading - ignored')
        try:
            with open('workload-data.csv', 'r') as f:
                lines = csv.reader(f)
                linenum = 0
                for line in lines:
                        if linenum != 0:
                                if line[1] not in self.workload_data:
                                        self.workload_data[line[1]]=[]
                                data = {}
                                for i in range(2, len(self.col)):
                                        data[self.col[i]]=float(line[i])
                                self.workload_data[line[1]].append(data)
                        linenum += 1
        except OSError as e:
            log.debug('cannot open workload-data.csv for reading (execption=%s) - recreating', e)
            with open('workload-data.csv', 'w') as f:
                f.write(','.join(self.col)+ '\n')
        self.datafile = open('workload-data.csv', 'a')
        self.datawriter = csv.writer(self.datafile)

    def set_mode(self, mode):
        self.mode = mode
        if mode == DETECT_MODE:
            self.build_model()
        elif mode == COLLECT_MODE:
            headline = None
            try:
                with open(UTIL_FILE, 'r') as utilf:
                    headline = utilf.readline()
            except Exception:
                log.debug('cannot open %r for reading - ignore', UTIL_FILE)

            if headline != 'TIME,UTIL':
                with open(UTIL_FILE, 'w') as utilf:
                    utilf.write('TIME,UTIL\n')

    def process_lc_max(self):
        try:
            udf = pd.read_csv(UTIL_FILE)
        except OSError as e:
            raise Exception('cannot run in "detect" mode without %r file (please run in collect mode first)!' % UTIL_FILE) from e


        lcu = udf['UTIL']
        maxulc = int(lcu.max())
        self.threshold['lcutilmax'] = maxulc
        log.debug('max LC utilization: %f', maxulc)

    def build_model(self):
        self.process_lc_max()
        for cid in self.workload_meta:
            if cid not in self.workload_data:
                continue
            log.debug('building model for %r', cid)
            meta = self.workload_meta[cid]
            data = self.workload_data[cid]
            utilization_partition = thresh.partition_utilization(meta['cpus'], 50)
            utilization_threshold = meta['cpus'] * 95.0
            tdp_data = list(filter(lambda x: x[Metric.UTIL] >= utilization_threshold, data))
            util = list(map(lambda x: x[Metric.UTIL], tdp_data))
            freq = list(map(lambda x: x[Metric.NF], tdp_data))
            if cid not in self.threshold:
                self.threshold[cid] = {"tdp": {}, "thresh": []}
            if len(util) > 0:
                mean, std = stats.norm.fit(freq)
                min_freq = min(freq)
                fbar = mean - 3 * std
                if min_freq < fbar:
                    fbar = min_freq
                self.threshold[cid]['tdp'] = {
                    'util': utilization_threshold,
                    'mean': mean,
                    'std': std,
                    'bar': fbar}
            for index, util in enumerate(utilization_partition):
                log.debug('building model for %r for util = %r', cid, util)
                try:
                    lower_bound = util
                    if index != len(utilization_partition) - 1:
                        higher_bound = utilization_partition[index + 1]
                    else:
                        higher_bound = lower_bound + 50
                    jdata = list(filter(
                        lambda x: (x[Metric.UTIL] >= lower_bound and
                                   x[Metric.UTIL] <= higher_bound), data))
                    if len(jdata) == 0:
                        log.warning('no enough model for %r for util=%r',
                                    cid, util)
                        continue
                    cpi = list(map(lambda x: x[Metric.CPI], jdata))
                    cpi_thresh = thresh.get_fense(cpi, True)
                    mpki = list(map(lambda x: x[Metric.L3MPKI], jdata))
                    mpki_thresh = thresh.get_fense(mpki, True)
                    memb = list(map(lambda x: x[Metric.MB], jdata))
                    mb_thresh = thresh.get_fense(memb, False)
                    self.threshold[cid]["thresh"].append({
                        "util_start": lower_bound,
                        "util_end": higher_bound,
                        "cpi": cpi_thresh,
                        "mpki": mpki_thresh,
                        "mb": mb_thresh})
                except Exception:
                    log.exception('error model budiling util=%r (%r)',
                                  cid, util)
        with open("threshold.json", 'w') as f:
            f.write(json.dumps(self.threshold))

    def add_workload_meta(self, cid, meta):
        self.workload_meta[cid] = meta
        with open("workload-meta.json", 'w') as f:
            f.write(json.dumps(self.workload_meta))

    def add_workload_data(self, app, name, data):
        self.count = self.count + 1
        if app not in self.workload_data:
            self.workload_data[app] = []
        self.workload_data[app].append(copy.deepcopy(data))
        row = [name, app, time.time()]
        for i in range(3, len(self.col)):
                row.append(data[self.col[i]])
        self.datawriter.writerow(row)
        if self.count % 10 == 0:
            self.datafile.flush()

    def add_lc_util(self, timestamp, lcutil):
        with open(UTIL_FILE, 'a') as utilf:
            utilf.write(str(timestamp) + ',' + str(lcutil) + '\n')
