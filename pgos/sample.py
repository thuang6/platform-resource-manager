#! /usr/bin/python

# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# SPDX-License-Identifier: Apache-2.0
#
from ctypes import *

class cgroup(Structure):
    _fields_ = [("path", c_char_p), 
                ("cid", c_char_p), 
                ("instructions", c_ulonglong),
                ("cycles", c_ulonglong),
                ("llc_misses", c_ulonglong),
                ("stall_l2_misses", c_ulonglong),
                ("stalls_memory_load", c_ulonglong),
                ("llc_occupancy", c_ulonglong),
                ("mbm_local", c_double),
                ("mbm_remote", c_double)]

class context(Structure):
    _fields_ = [("core", c_int),
               ("period", c_int),
               ("cgroup_count", c_int),
               ("timestamp", c_ulonglong),
               ("cgroups", POINTER(cgroup))]

lib = cdll.LoadLibrary('./libpgos.so')
lib.collect.argtypes = [context]
lib.collect.restype = context

cg = cgroup()
cg.path = '/sys/fs/cgroup/perf_event/docker/d144c76a22b3000278a42c516f374a65d759bf03226dda1c8f93ff05ee528f63/'.encode()
cg.cid = 'stressng'.encode()

ctx = context()
ctx.core = 22
ctx.period = 20
ctx.cgroup_count = 1
ctx.cgroups = (cgroup * 1)(cg)

ret = lib.collect(ctx)
print(ret.cgroups[0].instructions, ret.cgroups[0].cycles, ret.cgroups[0].llc_misses, ret.cgroups[0].stall_l2_misses,
      ret.cgroups[0].stalls_memory_load, ret.cgroups[0].llc_occupancy, ret.cgroups[0].mbm_local, ret.cgroups[0].mbm_remote)