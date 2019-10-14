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

""" This module implements platform metrics analysis and model build """

from __future__ import print_function
import logging
from collections import defaultdict
from enum import Enum
import json
from scipy import stats
import numpy as np
import pandas as pd

from .gmmfense import GmmFense
from .model import DistriModel
log = logging.getLogger(__name__)


class ThreshType(str, Enum):
    METRICS = 'metrics_threshold'
    TDP = 'tdp_threshold'


class Metric(str, Enum):
    """ This enumeration defines calculated metrics from wca measurements """
    CYC = 'cycle'
    INST = 'instruction'
    L3MISS = 'cache_miss'
    L3OCC = 'cache_occupancy'
    MB = 'memory_bandwidth_total'
    MBL = 'memory_bandwidth_local'
    MBR = 'memory_bandwidth_remote'
    CPI = 'cycles_per_instruction'
    L3MPKI = 'cache_miss_per_kilo_instruction'
    NF = 'normalized_frequency'
    UTIL = 'cpu_utilization'
    L2STALL = 'stalls_l2_miss'
    MEMSTALL = 'stalls_mem_load'
    L2SPKI = 'stalls_l2miss_per_kilo_instruction'
    MSPKI = 'stalls_memory_load_per_kilo_instruction'
    LCCAPACITY = 'latency_critical_utilization_capacity'
    LCMAX = 'latency_critical_utilization_max'
    SYSUTIL = 'system_utilization'


class Analyzer:
    UTIL_FILE = 'util.csv'
    METRIC_FILE = 'metric.csv'
    THRESH_FILE = 'threshold.json'
    UTIL_BIN_STEP = 50

    def __init__(self, wl_file=None, thresh_file=THRESH_FILE):
        if wl_file:
            try:
                with wl_file as wlf:
                    self.workload_meta = json.loads(wlf.read())
            except Exception as e:
                log.exception('cannot read workload file - stopped')
                raise e

        self.thresh_file = thresh_file
        try:
            with open(thresh_file, 'r') as threshf:
                self.threshold = json.loads(threshf.read())
        except Exception:
            self.threshold = {}

    def partition_utilization(self, cpu_number, step=UTIL_BIN_STEP, ratio=0.3):
        """
        Partition utilizaton bins based on requested CPU number and step count
            cpu_number - processor count assigned to workload
            step - bin range of one partition, default value is half processor
        """
        utilization_upper = (cpu_number + 1) * 100
        utilization_lower = cpu_number * 50

        utilization_bar = np.arange(utilization_lower, utilization_upper, step)

        return utilization_bar

    def _build_tdp_thresh(self, jdata):
        job = jdata['name'].values[0]
        if job not in self.workload_meta:
            return
        cpu_no = self.workload_meta[job]['cpus']

        utilization_threshold = cpu_no * 100 * 0.95
        tdp_data = jdata[jdata[Metric.UTIL] >= utilization_threshold]

        util = tdp_data[Metric.UTIL]
        freq = tdp_data[Metric.NF]

        if not util.empty:
            mean, std = stats.norm.fit(freq)

            min_freq = min(freq)
            fbar = mean - 3 * std
            if min_freq < fbar:
                fbar = min_freq
            self.threshold[job][ThreshType.TDP.value] = {
                'util': utilization_threshold,
                'mean': mean.item(),
                'std': std.item(),
                'bar': np.float64(fbar).item()}

    def _get_fense_origin(self, mdf, is_upper, strict, span, prob):
        gmm_fense = GmmFense(mdf.values.reshape(-1, 1), prob)
        if strict:
            return gmm_fense.get_strict_fense(is_upper, span)

        return gmm_fense.get_normal_fense(is_upper, span)

    def _get_fense(self, mdf, is_upper, strict, span, prob, use_origin):
        if use_origin is True:
            return self._get_fense_origin(mdf, is_upper, strict, span, prob)

        gmm_fense = GmmFense(mdf.values.reshape(-1, 1), prob)

        return gmm_fense.get_gaussian_round_fense(is_upper, strict, span)

    def _build_thresh(self, jdata, ratio, span, prob, strict, use_origin, verbose):
        job = jdata['name'].values[0]
        if job not in self.workload_meta:
            return
        cpu_no = self.workload_meta[job]['cpus']
        utilization_partition = self.partition_utilization(
            cpu_no, Analyzer.UTIL_BIN_STEP)
        length = len(utilization_partition, ratio)

        for index, util in enumerate(utilization_partition):
            lower_bound = util
            if index != length - 1:
                higher_bound = utilization_partition[index + 1]
            else:
                higher_bound = lower_bound + Analyzer.UTIL_BIN_STEP
            try:
                jdataf = jdata[(jdata[Metric.UTIL] >= lower_bound) &
                               (jdata[Metric.UTIL] <= higher_bound)]
                cpi = jdataf[Metric.CPI]
                cpi_thresh = self._get_fense(cpi, True, strict,
                                             span, prob, use_origin)
                mpki = jdataf[Metric.L3MPKI]
                mpki_thresh = self._get_fense(mpki, True, strict,
                                              span, prob, use_origin)
                if Metric.MB in jdataf.columns:
                    memb = jdataf[Metric.MB]
                else:
                    memb = jdataf[Metric.MBL] + jdataf[Metric.MBR]
                mb_thresh = self._get_fense(memb, False, strict,
                                            span, prob, use_origin)
                thresh = {
                    'util_start': lower_bound.item(),
                    'util_end': higher_bound.item(),
                    'cpi': np.float64(cpi_thresh).item(),
                    'mpki': np.float64(mpki_thresh).item(),
                    'mb': np.float64(mb_thresh).item()
                }
                if Metric.L2SPKI in jdataf.columns:
                    l2spki = jdataf[Metric.L2SPKI]
                    l2spki_thresh = self._get_fense(l2spki, True, strict,
                                                    span, prob, use_origin)
                    thresh['l2spki'] = np.float64(l2spki_thresh).item()
                if Metric.MSPKI in jdataf.columns:
                    mspki = jdataf[Metric.MSPKI]
                    mspki_thresh = self._get_fense(mspki, True, strict,
                                                   span, prob, use_origin)
                    thresh['mspki'] = np.float64(mspki_thresh).item()
                self.threshold[job][ThreshType.METRICS.value].append(thresh)
            except Exception as e:
                print(str(e))

    def _process_lc_max(self, util_file):
        udf = pd.read_csv(util_file)
        lcs = udf[udf['name'] == 'lcs']
        lcu = lcs[Metric.UTIL]
        maxulc = int(lcu.max())
        self.threshold['lcutilmax'] = maxulc
        log.debug('max LC utilization: %f', maxulc)

    def _write_threshold_file(self):
        with open(self.thresh_file, 'w') as threshf:
            json.dump(self.threshold, threshf, indent=4)

    def get_lcutilmax(self):
        return self.threshold.get('lcutilmax', 0)

    def get_wl_meta(self):
        return self.workload_meta

    def update_lcutilmax(self, lc_utils):
        self.threshold['lcutilmax'] = lc_utils
        self._write_threshold_file()

    def get_thresh(self, cpu_model, ncpu, job, thresh_type):
        return self.threshold[cpu_model][job][ncpu][thresh_type] if cpu_model in self.threshold and\
            job in self.threshold[cpu_model] and ncpu in self.threshold[cpu_model][job] else {}

    def build_model(self, util_file=UTIL_FILE, metric_file=METRIC_FILE, ratio=0.5,
                    span=3, prob=0.05, strict=True, use_origin=False, verbose=False):
        if self.threshold:
            return
        
        # initialize a three-level nested dict
        self.threshold = defaultdict(lambda: defaultdict(dict))

        model_builder = DistriModel(ratio, span, prob, strict, use_origin, verbose)
        #self._process_lc_max(util_file)
        mdf = pd.read_csv(metric_file)
        model_keys = mdf.groupby(['cpu_model', 'name', 'vcpu_count']).groups.keys()
        for model_key in model_keys:
            # filter dataframe by cpu_model, application, cpu_assignment
            if any(str(v) == 'nan' for v in model_key):
                continue
            jdata = mdf[(mdf['cpu_model'] == model_key[0]) &
                           (mdf['name'] == model_key[1]) &
                           (mdf['vcpu_count'] == model_key[2])]
            cpu_number = model_key[2]
            tdp_thresh, thresholds = model_builder.build_model(jdata, cpu_number)

            value = {ThreshType.TDP.value: tdp_thresh, ThreshType.METRICS.value: thresholds}
            self.threshold[model_key[0]][model_key[1]][model_key[2]] = value

        if self.threshold:
            if verbose:
                log.warn(self.threshold)
            self._write_threshold_file()
        else:
            log.warn('Fail to build model, no enough data were collected!')
