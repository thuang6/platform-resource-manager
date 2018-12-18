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

""" This module contains the parameters """


class ConfigConstants:
    verbose = 2

    min_data_points = 20
    lower_util_bound = 0.5
    step = 50
    use_ratio = True
    step_ratio = 0.3

    rand_seed = 1
    max_components = 10

    outlier_span = 3
    check_strict = False

    check_chi_square_test = False
    chi_square_test_threshold = 0.95
    check_f_measure = True
    f_measure_threshold = 0.6
    check_accuracy = False
    accuracy_threshold = 0.5
    information_gain_threshold = 0.2
