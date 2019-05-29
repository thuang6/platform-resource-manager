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

import logging
import time
from typing import List, Union, Optional
from datetime import datetime, timedelta
from wca.runners import Runner
from prm.model_distribution.metric import Metric
from prm.model_distribution.processing import PromProcessor
from prm.model_distribution.model import DistriModel
from prm.model_distribution.db import ModelDatabase
from prm.analyze.analyzer import ThreshType

log = logging.getLogger(__name__)


class ImproperStepError(Exception):
    """exceeded maximum resolution of 11,000 points per timeseries for Prometheus. """


class BuilderRunner(Runner):
    """
    BuildModel TODO runner run iterations to build model thresholds and store them in database.
    Arguments:
        prometheus_host: prometheus database host
        database: model storage database, get/set api is provided
        model: threshold analyer
        cycle:iteration cycle in seconds
            (default to 3600 second )
        time_range: query range of prometheus database
            (default to 86400 seconds)
        step: query resolution step width of prometheus
            (default to 10 seconds)
        timeout: timeout of connecting the prometheus database
            (default to 1 second)
    """

    def __init__(
        self,
        prometheus_host: str,
        database: ModelDatabase,
        model: DistriModel,
        cycle: Union[float, int, None],
        time_range: Union[str, float, int, None],
        step: Union[str, float, int, None],
        timeout: Union[float, int, None],
    ):
        self._prometheus_host = prometheus_host
        self._cycle = 3600 if cycle is None else cycle
        self._time_range = 86400 if time_range is None else time_range
        self._step = 10 if step is None else step
        self._timeout = 1 if timeout is None else timeout
        self._database = database
        self._model = model
        self._finish = False
        self._url = self.get_url_of_prom()

        self.metrics_names = [Metric.MB, Metric.MBL, Metric.MBR, Metric.CPI,
                              Metric.L3MPKI, Metric.NF, Metric.UTIL, Metric.L2SPKI, Metric.MSPKI]

        self.prom_processor = PromProcessor(self._url, self._timeout)
        self._last_iteration = time.time()

    def _start_end_of_timestamp_now(self):
        """change datetime to unix timestamp format"""

        if self._time_range/self._step > 11000:
            raise ImproperStepError("step {} is too small for timerange {}, which exceeded maximum resolution of 11,000 points per timeseries.".format(
                self._step, _time_range))

        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=self._time_range)
        end = time.mktime(end_time.timetuple())
        start = time.mktime(start_time.timetuple())
        return start, end

    def get_url_of_prom(self):
        return self._prometheus_host

    def _get_existing_models(self, start, end):
        """query all workload,cpu_model,cpu_assignments combinations in promethus database
        """
        models = self.prom_processor.generate_existing_models_by_cpu_util(
            start, end)
        return models

    def _initialize(self):
        pass

    def _wait(self):
        """Decides how long one iteration should take.
        Additionally calculate residual time, based on time already taken by iteration.
        """
        now = time.time()

        iteration_duration = now - self._last_iteration

        self._last_iteration = now

        residual_time = max(0., self._cycle - iteration_duration)
        log.info('waiting for next iteration')
        time.sleep(residual_time)

    def run(self) -> int:
        log.info('model-distribution runner is started!')

        while True:
            self._iterate()

            if self._finish:
                break
        return 0

    def _iterate(self):
        log.info('new iteration start now!')

        start, end = self._start_end_of_timestamp_now()
        log.info('query data range from {} to {}: '.format(start, end))
        model_keys, nested_trees = self._get_existing_models(start, end)

        for model_key in model_keys:
            label_group = model_key._asdict()
            dataframe = self.prom_processor.generate_new_metric_dataframe(
                self.metrics_names, label_group, start, end, self._step)

            tdp_thresh, thresholds = self._model.build_model(
                dataframe, label_group)

            value = {ThreshType.TDP: tdp_thresh, ThreshType.METRICS: thresholds}

            nested_trees[model_key.cpu_model][model_key.application][model_key.initial_task_cpu_assignment] = value

        self._store_database(nested_trees)
        self._wait()

    def _store_database(self, nested_trees):
        for key, value in nested_trees.items():
            self._database.set(key, value)

