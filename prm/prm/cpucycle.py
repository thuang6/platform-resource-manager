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

""" This module implements CPU cycle control based on CFS quota """

from __future__ import print_function
from __future__ import division

import logging
from typing import Union

from datetime import datetime
from prm.resource import Resource

from owca.allocators import AllocationType

log = logging.getLogger(__name__)

class CpuCycle(Resource):
    """ This class is the resource class of CPU cycle """
    CPU_QUOTA_MIN = 0.001
    CPU_QUOTA_CORE = 100000
    CPU_QUOTA_PERCENT = CPU_QUOTA_CORE / 100
    CPU_QUOTA_HALF_CORE = CPU_QUOTA_CORE * 0.5

    def __init__(self, sysMaxUtil, minMarginRatio, verbose):
        super(CpuCycle, self).__init__()
        self.min_margin_ratio = minMarginRatio
        self.update_max_sys_util(sysMaxUtil)
        self.update()
        self.verbose = verbose
        self.cur_allocs = None
        self.new_allocs = None

    def update_allocs(self, cur_allocs, new_allocs, ncpu):
        self.cur_allocs = cur_allocs
        self.new_allocs = new_allocs
        self.ncpu = ncpu

    def update(self):
        if self.is_min_level():
            self.cpu_quota = CpuCycle.CPU_QUOTA_MIN
        else:
            self.cpu_quota = self.quota_level * int(self.quota_step)

    def update_max_sys_util(self, lc_max_util):
        """
        Update quota max and step based on given LC system maximal utilization
        monitored
            lc_max_util - maximal LC workloads utilization monitored
        """
        self.quota_max = lc_max_util / 100 / self.ncpu 
        self.quota_step = self.quota_max / Resource.BUGET_LEV_MAX
        
    def __set_alloc(self, task_id, alloc_type: AllocationType, alloc: float):
        is_new = True
        if task_id in self.cur_allocs and\
            alloc_type in self.cur_allocs[task_id] and\
            alloc == self.cur_allocs[task_id][alloc_type]:
            is_new = False
        
        if is_new:
            if task_id in self.new_allocs:
                task_allocs = self.new_allocs[task_id]
            else:
                task_allocs= dict()
                self.new_allocs[task_id] = task_allocs
            task_allocs[alloc_type] = alloc
            
    def set_share(self, cid, share: float):
        self.__set_alloc(cid, AllocationType.SHARES, share)

    def __set_quota(self, cid, quota):
        self.__set_alloc(cid, AllocationType.QUOTA, quota)
        log.info('set task %s cpu quota to %i', cid, quota)

    def budgeting(self, bes, lcs):
        newq = int(self.cpu_quota / len(bes))
        for cid in bes:
            self.__set_quota(cid, newq)

    def detect_margin_exceed(self, lc_utils, be_utils):
        """
        Detect if BE workload utilization exceed the safe margin
            lc_utils - utilization of all LC workloads
            be_utils - utilization of all BE workloads
        """
        margin = self.min_margin_ratio / self.ncpu

        if self.verbose:
            log.debug('lcUtils: %i, beUtils: %i, margin: %i, quota max %i',
                lc_utils, be_utils, margin * self.ncpu * 100,
                self.quota_max * self.ncpu * 100)

        exceed = lc_utils == 0 or lc_utils + be_utils + margin > self.quota_max

        hold = lc_utils + be_utils + margin + self.quota_step >= self.quota_max

        return (exceed, hold)
