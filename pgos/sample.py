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
    _fields_ = [("ret", c_int),
                ("path", c_char_p), 
                ("cid", c_char_p), 
                ("instructions", c_ulonglong),
                ("cycles", c_ulonglong),
                ("llc_misses", c_ulonglong),
                #("stall_l2_misses", c_ulonglong),
                ("stalls_memory_load", c_ulonglong),
                ("offcore_req_l3_miss_data_rd", c_ulonglong),
                #("mem_load_retired_local_pmm", c_ulonglong),
                #("mem_load_l3miss_retired_remote_pmm", c_ulonglong),
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

lib = cdll.LoadLibrary('./libpgos.so')
lib.collect.argtypes = [context]
lib.collect.restype = context


cg0 = cgroup()
cg0.path = '/sys/fs/cgroup/perf_event/docker/be776bd43908215671ae5eeb98dd0d0bd7251043d332956960b9a6fc2dc51342/'.encode()
cg0.cid = 'cassandra'.encode()

cg1 = cgroup()
cg1.path = '/sys/fs/cgroup/perf_event/docker/6985ab1fccd4346783f7da8598a165373ed5024dbe5f0b22281f6c05ccb3880a/'.encode()
cg1.cid = 'memcache'.encode()
ctx = context()
ctx.core = 72
ctx.period = 10000
ctx.cgroup_count = 2
ctx.cgroups = (cgroup * 2)(cg0, cg1)

ret = lib.pgos_init()
print(ret)

for i in range(5):
      ret = lib.collect(ctx)
      cg = ret.cgroups[0]
      #print(cg.ret, cg.instructions, cg.cycles, cg.llc_misses, cg.stall_l2_misses,
      print(cg.ret, cg.instructions, cg.cycles, cg.llc_misses,
            cg.stalls_memory_load, cg.offcore_req_l3_miss_data_rd, 
            #cg.stall_l2_misses, cg.stalls_memory_load, cg.mem_load_retired_local_pmm, cg.mem_load_l3miss_retired_remote_pmm,
            cg.llc_occupancy, cg.mbm_local, cg.mbm_remote)
      cg = ret.cgroups[1]
      print(cg.ret, cg.instructions, cg.cycles, cg.llc_misses,
            cg.stalls_memory_load, cg.offcore_req_l3_miss_data_rd,
            #cg.stall_l2_misses, cg.stalls_memory_load, cg.mem_load_retired_local_pmm, cg.mem_load_l3miss_retired_remote_pmm,
            cg.llc_occupancy, cg.mbm_local, cg.mbm_remote)

lib.pgos_finalize()
