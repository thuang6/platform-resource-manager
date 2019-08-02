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

""" This module scores a rule in terms of its discriminating capability """

import math
import numpy as np
import scipy
import configConstants


class Scoring(object):
    @staticmethod
    def score(total, positive, sub_total, sub_positive):
        score = 0
        if configConstants.ConfigConstants.check_chi_square_test:
            score = Scoring.chi_square_test(total, positive, sub_total, sub_positive)
            if score <= 0:
                return 0
        if configConstants.ConfigConstants.check_f_measure:
            f_measure = Scoring.calc_f_measure(total, positive, sub_total, sub_positive)
            f_measure2 = Scoring.calc_f_measure(
                total, total - positive, total - sub_total,
                (total - positive) - (sub_total - sub_positive))
            if configConstants.ConfigConstants.verbose > 6:
                output_str = "    2 f-measures: " + str(f_measure) + ", " + str(f_measure2)
                print(output_str)
            f_measure = (f_measure + f_measure2) / 2
            if configConstants.ConfigConstants.verbose > 6:
                output_str = "    F-measure: " + str(f_measure)
                print(output_str)
            if f_measure < configConstants.ConfigConstants.f_measure_threshold:
                return 0
            return f_measure
        score = Scoring.calc_information_gain(total, positive, sub_total, sub_positive)
        return score

    @staticmethod
    def calc_accuracy(total, positive, sub_total, sub_positive):
        accuracy = sub_positive
        accuracy += ((total - positive) - (sub_total - sub_positive))
        accuracy = float(accuracy) / float(total)
        if configConstants.ConfigConstants.verbose > 6:
            output_str = "    Accuracy: " + str(accuracy)
            print(output_str)
        return accuracy

    @staticmethod
    def calc_f_measure(total, positive, sub_total, sub_positive):
        precision = Scoring.calc_binomial_lower_bound(sub_total, sub_positive)
        recall = Scoring.calc_binomial_lower_bound(positive, sub_positive)
        f_measure = 0
        if precision + recall > 0:
            f_measure = 2 * precision * recall / (precision + recall)
        return f_measure

    @staticmethod
    def calc_binomial_lower_bound(total, positive):
        total += 1
        positive += 0.5
        p = float(positive) / float(total)
        stdev = math.sqrt(p * (1 - p) / total)
        return p - stdev * 2

    @staticmethod
    def chi_square_test(total, positive, sub_total, sub_positive):
        a00 = sub_positive
        a01 = sub_total - sub_positive
        a10 = positive - sub_positive
        a11 = (total - positive) - (sub_total - sub_positive)
        if a00 + a01 > 0 and a10 + a11 > 0 and a00 + a10 > 0 and a01 + a11 > 0:
            obs = np.array([[a00, a01], [a10, a11]], np.int32)
            _, p_val, _, _ = scipy.stats.chi2_contingency(obs)
            if (configConstants.ConfigConstants.verbose > 6):
                output_str = "    Chi-square test: " + str(p_val)
                print(output_str)
            if (1 - p_val >= configConstants.ConfigConstants.chi_square_test_threshold):
                return 1 - p_val
        return 0

    @staticmethod
    def calc_information_gain(total, positive, sub_total, sub_positive):
        i = Scoring.calc_binary_entropy(total, positive)
        ci1 = Scoring.calc_binary_entropy(sub_total, sub_positive)
        ci2 = Scoring.calc_binary_entropy(total - sub_total, positive - sub_positive)
        ig = ci1 * float(sub_total / total) + ci2 * (1 - float(sub_total) / float(total)) - i
        if configConstants.ConfigConstants.verbose > 6:
            output_str = "    Information gain: " + str(ig)
            print(output_str)
        if (ig < configConstants.ConfigConstants.information_gain_threshold
                and not configConstants.ConfigConstants.check_chi_square_test):
            ig = -1
        return ig

    @staticmethod
    def calc_binary_entropy(total, positive):
        if positive == 0 or positive == total:
            return 0
        p = float(positive) / float(total)
        return p * math.log(p, 2) + (1 - p) * math.log(1 - p, 2)
