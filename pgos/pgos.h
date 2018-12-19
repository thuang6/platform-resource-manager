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
#ifndef PGOS_H
#define PGOS_H

#include <pqos.h>
#include <stdint.h>
#include <sys/types.h>

int pgos_mon_start_pids(unsigned pid_num, pid_t *pids);
struct pqos_event_values pgos_mon_poll(int index);
void pgos_mon_stop();

#endif