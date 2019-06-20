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
#include "helper.h"
#include <linux/perf_event.h>

void set_attr_disabled(struct perf_event_attr *attr, int disabled) {
	attr->disabled = disabled;
}

void set_attr_precise_ip(struct perf_event_attr *attr, unsigned char precise_ip) {
	attr->sample_period = 1000;
	attr->sample_type |= PERF_SAMPLE_IP;
	attr->precise_ip = precise_ip;
}

struct cgroup* get_cgroup(struct cgroup *cgroups, int index) {
    return cgroups + index;
}
