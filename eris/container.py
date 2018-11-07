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

"""
This module implements resource contention detection on one workload
"""

from __future__ import print_function
from __future__ import division

import subprocess
import time

from collections import deque
from datetime import datetime
from enum import Enum
from os.path import join as path_join


class Contention(Enum):
    """ This enumeration defines resource contention type """
    UNKN = 1
    CPU_CYC = 2
    LLC = 3
    MEM_BW = 4
    TDP = 5


class Container(object):
    """
    This class is the abstraction of one task, container metrics and
    contention detection method are encapsulated in this module
    """

    def __init__(
            self, cgroup_driver, cid, name, pids, verbose,
            thresh=[], tdp_thresh=[], history_depth=5):
        self.cid = cid
        self.name = name
        self.pids = pids
        self.cpu_usage = 0
        self.utils = 0
        self.timestamp = 0.0
        self.thresh = thresh
        self.tdp_thresh = tdp_thresh
        self.verbose = verbose
        self.metrics = dict()
        self.history_depth = history_depth + 1
        self.metrics_history = deque([], self.history_depth)
        self.cpusets = []
        if cgroup_driver == 'systemd':
            self.con_path = 'docker-' + cid + '.scope'
            self.parent_path = 'system.slice/'
        else:
            self.con_path = cid
            self.parent_path = 'docker/'

    def __str__(self):
        metrics = self.metrics
        cols = [
            metrics['TIME'].isoformat(),
            self.cid,
            self.name,
            metrics['INST'],
            metrics['CYC'],
            metrics['CPI'],
            metrics['L3MPKI'],
            metrics['L3MISS'],
            metrics['NF'],
            self.utils,
            metrics['L3OCC'],
            metrics['MBL'],
            metrics['MBR'],
            metrics['L2STALL'],
            metrics['MEMSTALL'],
            metrics['L2SPKI'],
            metrics['MSPKI'],
        ]
        return ','.join(str(col) for col in cols) + '\n'

    def get_history_delta_by_type(self, column_name):
        length = len(self.metrics_history)
        if length == 0:
            return 0
        if length == 1:
            return self.metrics_history[0][column_name]

        data_sum = sum(m[column_name] for m in self.metrics_history[:-1])
        data_avg = float(data_sum) / (length - 1)
        data_delta = self.metrics_history[-1][column_name] - data_avg

        return data_delta

    def get_llcoccupany_delta(self):
        return self.get_history_delta_by_type('L3OCC')

    def get_freq_delta(self):
        return self.get_history_delta_by_type('NF')

    def get_latest_mbt(self):
        mbl = self.metrics.get('MBL', 0)
        mbr = self.metrics.get('MBR', 0)

        return mbl + mbr

    def get_metrics(self):
        """ retrieve container platform metrics """
        return self.metrics

    def update_pids(self, pids):
        """
        update process ids of one Container
            pids - pid list of Container
        """
        self.pids = pids

    def update_cpu_usage(self):
        """ calculate cpu usage of container """
        try:
            cur = time.time() * 1e9
            filename = path_join('/sys/fs/cgroup/cpu/docker',
                                 self.cid, 'cpuacct.usage')
            with open(filename, 'r') as f:
                usage = int(f.read().strip())
                if self.cpu_usage != 0:
                    self.utils = (usage - self.cpu_usage) * 100 /\
                        (cur - self.timestamp)
                self.cpu_usage = usage
                self.timestamp = cur
        except (ValueError, IOError):
            pass

    def update_metrics_history(self):
        '''
        add metric data to metrics history
        metrics history only contains the most recent metrics data, defined by
        self.historyDepth if histroy metrics data length exceeds the
        self.historyDepth, the oldest data will be erased
        '''
        self.metrics_history.append(self.metrics.copy())

    def __detect_in_bin(self, thresh):
        metrics = self.metrics
        if metrics['CPI'] > thresh['cpi']:
            if metrics['L3MPKI'] > thresh['mpki']:
                print('Last Level Cache contention is detected at ' +
                      datetime.now().isoformat(' '))
                print('Latency critical container ' + self.name + ', CPI = ' +
                      str(metrics['CPI']) + ', MKPI = ' +
                      str(metrics['L3MPKI']) + '\n')
                return Contention.LLC
            if metrics['MBL'] + metrics['MBR'] < thresh['mb']:
                print('Memory Bandwidth contention detected at ' +
                      datetime.now().isoformat(' '))
                print('Latency critical container ' + self.name + ', CPI = ' +
                      str(metrics['CPI']) + ', MBL = ' + str(metrics['MBL']) +
                      ', MBR = ' + str(metrics['MBR']) + '\n')
                return Contention.MEM_BW

            print('Performance is impacted at ' +
                  datetime.now().isoformat(' '))
            print('Latency critical container ' + self.name +
                  ' CPI exceeds threshold, value = ', str(metrics['CPI']))
            return Contention.UNKN

        return None

    def tdp_contention_detect(self):
        """ detect TDP contention in container """
        if not self.tdp_thresh:
            return None

        if self.verbose:
            print(self.utils, self.metrics['NF'], self.tdp_thresh['util'],
                  self.tdp_thresh['bar'])

        if self.utils >= self.tdp_thresh['util'] and\
           self.metrics['NF'] < self.tdp_thresh['bar']:
            print('TDP Contention Alert!')
            return Contention.TDP

        return None

    def contention_detect(self):
        """ detect resouce contention after find proper utilization bin """
        if not self.thresh:
            return None

        for i in range(0, len(self.thresh)):
            thresh = self.thresh[i]
            if self.utils < thresh['util_start']:
                if i == 0:
                    return None

                return self.__detect_in_bin(self.thresh[i - 1])

            if self.utils >= thresh['util_start']:
                if self.utils < thresh['util_end'] or\
                   i == len(self.thresh) - 1:
                    return self.__detect_in_bin(thresh)
