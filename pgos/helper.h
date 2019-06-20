// Copyright (C) 2018 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions
// and limitations under the License.
//
//
// SPDX-License-Identifier: Apache-2.0
//
#ifndef HELPER_H
#define HELPER_H
#include <linux/perf_event.h>
#include <stdint.h>

struct cgroup {
    int ret;
    char* path;
    char* cid;
    //uint64_t instructions, cycles, llc_misses, stalls_memory_load, mem_load_l3miss_retired_remote_pmm, llc_occupancy;
    uint64_t instructions, cycles, llc_misses, stalls_memory_load, mem_load_retired_local_pmm, llc_occupancy;
    //uint64_t instructions, cycles, llc_misses, stalls_l2_misses, stalls_memory_load, mem_load_retired_local_pmm, llc_occupancy;
    double mbm_local, mbm_remote;
};

struct context {
    int ret;
    int core;
    int period;
    int cgroup_count;

    uint64_t timestamp;
    struct cgroup *cgroups;
};

struct cgroup* get_cgroup(struct cgroup *cgroups, int index);

void set_attr_disabled(struct perf_event_attr *attr, int disabled);

void set_attr_precise_ip(struct perf_event_attr *attr, unsigned char precise_ip);
#endif
