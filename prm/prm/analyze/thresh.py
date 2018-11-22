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

import numpy as np
from prm.analyze.gmmfense import GmmFense


def get_fense(mdf, is_upper):
    """
    Get fense based on predefined fense type.
        args - arguments from command line input
        mdf - platform metrics dataframe
        is_upper - True if upper fense is needed,
                   False if lower fense is needed
    """
    gmm_fense = GmmFense(np.array(mdf).reshape(-1, 1))
    return gmm_fense.get_strict_fense(is_upper)


def partition_utilization(cpu_number, step=50):
    """
    Partition utilizaton bins based on requested CPU number and step count
        cpu_number - processor count assigned to workload
        step - bin range of one partition, default value is half processor
    """
    utilization_upper = (cpu_number + 1) * 100
    utilization_lower = cpu_number * 50

    utilization_bar = np.arange(utilization_lower, utilization_upper, step)

    return utilization_bar
