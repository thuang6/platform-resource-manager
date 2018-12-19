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

#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h>
#include <sys/ioctl.h>
#include <linux/perf_event.h>
#include <cpuid.h>
#include <asm/unistd.h>
#include <stdint.h>
#include <fcntl.h>
#include <errno.h>
#include "perf.h"

struct perf_event_spec{
	uint8_t event;
	uint8_t umask;
	uint8_t inv;
	uint8_t cmask;
	uint8_t edge;
};

struct x86_cpu_info {
	uint32_t display_model;
	uint32_t display_family;
};

static const struct perf_event_spec skl_spec[] = {
	{.event = 0xA3, .umask = 0x05, .cmask = 5},
	{.event = 0xA3, .umask = 0x14, .cmask = 20},
};

static const struct perf_event_spec brw_spec[] = {
	{.event = 0xA3, .umask = 0x05, .cmask = 5},
	{.event = 0xA3, .umask = 0x06, .cmask = 6},
};

struct x86_cpu_info get_x86_cpu_info(void) {
	uint32_t eax, ebx, ecx, edx;
	__cpuid(1, eax, ebx, ecx, edx);
	const uint32_t model = (eax >> 4) & 0xF;
	const uint32_t family = (eax >> 8) & 0xF;
	const uint32_t extended_model = (eax >> 16) & 0xF;
	const uint32_t extended_family = (eax >> 20) & 0xFF;
	uint32_t display_family = family;
	if (family == 0xF) {
		display_family += extended_family;
	}
	uint32_t display_model = model;
	if ((family == 0x6) || (family == 0xF)) {
		display_model += extended_model << 4;
	}
	return (struct x86_cpu_info) {
		.display_model = display_model,
			.display_family = display_family
	};
}

uint64_t get_config_of_event(uint32_t type,uint64_t event) {
	if (type == PERF_TYPE_HARDWARE) {
		return event;
	}

	struct x86_cpu_info cpu_info = get_x86_cpu_info();
	struct perf_event_spec spec;
	//printf("CPU family %x CPU model %x\n", cpu_info.display_family, cpu_info.display_model);
	if (cpu_info.display_family == 0x06) {
		switch (cpu_info.display_model) {
			case 0x4E:
			case 0x5E:
			case 0x55:
				/* Skylake */
				spec = skl_spec[event];
				break;
			case 0x3D:
			case 0x47:
			case 0x4F:
			case 0x56:
				/* Broadwell */
				spec = brw_spec[event];
				break;
		}
	}
	return  ((uint32_t) spec.event) | (((uint32_t) spec.umask) << 8) | (((uint32_t) spec.edge) << 18) 
		| (((uint32_t) spec.inv) << 23) | (((uint32_t) spec.cmask) << 24);	
}

