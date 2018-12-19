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
""" This module is a wrapper of libpgos and expose metrics monitor
interface"""

import sys
import traceback

from ctypes import cdll, Structure
from ctypes import c_char_p, c_ulonglong, c_double, c_int, POINTER
from analyze.analyzer import Metric


class cgroup(Structure):
    _fields_ = [("ret", c_int),
                ("path", c_char_p),
                ("cid", c_char_p),
                ("instructions", c_ulonglong),
                ("cycles", c_ulonglong),
                ("llc_misses", c_ulonglong),
                ("stalls_l2_misses", c_ulonglong),
                ("stalls_memory_load", c_ulonglong),
                ("llc_occupancy", c_ulonglong),
                ("mbm_local", c_double),
                ("mbm_remote", c_double)]


class context(Structure):
    _fields_ = [("ret", c_int),
                ("core", c_int),
                ("period", c_int),
                ("cgroup_count", c_int),
                ("timestamp", c_ulonglong),
                ("cgroups", POINTER(cgroup))]


class Pgos(object):
    """ This class wraps libpgos interface and provide eris friendly method """

    def __init__(self, num_core, period):
        lib = cdll.LoadLibrary('./libpgos.so')
        lib.collect.argtypes = [context]
        lib.collect.restype = context
        self.lib = lib
        ctx = context()
        ctx.core = num_core
        ctx.period = period
        self.ctx = ctx

    def init_pgos(self):
        return self.lib.pgos_init()

    def fin_pgos(self):
        self.lib.pgos_finalize()

    def collect(self, cgps):
        ctx = self.ctx
        ctx.cgroup_count = len(cgps)
        cg_array = []
        for cgp in cgps:
            cg = cgroup()
            cg.cid = cgp[0].encode()
            cg.path = cgp[1].encode()
            cg_array.append(cg)
        ctx.cgroups = (cgroup * len(cgps))(* cg_array)
        metrics = []
        try:
            res = self.lib.collect(ctx)
        except Exception:
            traceback.print_exc(file=sys.stdout)
        if res.ret == 0:
            for i in range(len(cgps)):
                cg = res.cgroups[i]
                if cg.ret != 0:
                    print('error in metrics collect for container: ' +
                          cg.cid.decode('utf-8') +
                          ', error code: ' + str(cg.ret))
                    continue
                metrics.append((cg.cid.decode('utf-8'),
                                {
                                    Metric.INST: cg.instructions,
                                    Metric.CYC: cg.cycles,
                                    Metric.L3MISS: cg.llc_misses,
                                    Metric.L2STALL: cg.stalls_l2_misses,
                                    Metric.MEMSTALL: cg.stalls_memory_load,
                                    Metric.L3OCC: cg.llc_occupancy,
                                    Metric.MBL: cg.mbm_local,
                                    Metric.MBR: cg.mbm_remote,
                                }))
        else:
            print('error in libpgos collect, error code:' + str(res.ret))

        return res.timestamp, metrics
