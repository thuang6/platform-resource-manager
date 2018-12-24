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

""" This module start a prometheus client and expose collected metrics """

from prometheus_client import Gauge, start_http_server


class PrometheusClient:
    def __init__(self):
        self.gauge_cpu_usage_percentage = Gauge('cma_cpu_usage_percentage',
                                                'CPU usage percentage of a\
                                                container', ['container'])
        self.gauge_llc_misses = Gauge('cma_llc_misses',
                                      'CPU usage percentage of a container',
                                      ['container'])
        self.gauge_unhalted_cycles = Gauge('cma_unhalted_cycles',
                                           'CPU usage percentage of a\
                                           container', ['container'])
        self.gauge_instructions = Gauge('cma_instructions',
                                        'Instructions of a container',
                                        ['container'])
        self.gauge_cycles_per_instruction = Gauge('cma_cycles_per_instruction',
                                                  'Cycles per instruction of a\
                                                  container', ['container'])
        self.gauge_misses_per_instruction = Gauge('cma_misses_per_instruction',
                                                  'Misses per instruction of a\
                                                  container', ['container'])
        self.gauge_stalls_mem_per_instruction = Gauge(
            'cma_stalls_mem_per_instruction',
            'Stalls memory load per instruction of a container', ['container'])
        self.gauge_average_frequency = Gauge('cma_average_frequency',
                                             'Instructions of a container',
                                             ['container'])
        self.gauge_memory_bandwidth = Gauge('cma_memory_bandwidth',
                                            'Instructions of a container',
                                            ['container'])
        self.gauge_llc_occupancy = Gauge('cma_llc_occupancy',
                                         'Instructions of a container',
                                         ['container'])

    def start(self):
        start_http_server(8080)

    def send_metrics(self, container_name, cpu_usage_percentage,
                     unhalted_cycle, llc_miss, instructions,
                     cycles_per_instruction, misses_per_instruction,
                     stalls_mem_load_per_instruction, average_frequency,
                     memory_bandwidth, llc_occupancy):
        self.gauge_cpu_usage_percentage.labels(container_name).set(
            cpu_usage_percentage)
        self.gauge_unhalted_cycles.labels(container_name).set(unhalted_cycle)
        self.gauge_llc_misses.labels(container_name).set(llc_miss)
        self.gauge_instructions.labels(container_name).set(instructions)
        self.gauge_cycles_per_instruction.labels(container_name).set(
            cycles_per_instruction)
        self.gauge_misses_per_instruction.labels(container_name).set(
            misses_per_instruction)
        self.gauge_stalls_mem_per_instruction.labels(container_name).set(
            stalls_mem_load_per_instruction)
        self.gauge_average_frequency.labels(container_name).set(
            average_frequency)
        self.gauge_memory_bandwidth.labels(container_name).set(
            memory_bandwidth)
        self.gauge_llc_occupancy.labels(container_name).set(llc_occupancy)
