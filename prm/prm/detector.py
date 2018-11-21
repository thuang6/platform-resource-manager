import logging
import numpy as np
from owca import detectors
from owca.platforms import Platform
from owca.detectors import ContentionAnomaly, TasksMeasurements
from owca.detectors import TasksResources, TasksLabels
from owca.detectors import ContendedResource
from owca.metrics import Metric as OwcaMetric

from prm.container import Container, Metric
from prm.analyze.analyze import Analyzer

log = logging.getLogger(__name__)


class ContentionDetector(detectors.AnomalyDetector):
    COLLECT_MODE = 'collect'
    DETECT_MODE = 'detect'

    def __init__(self, mode_config: str = 'collect'):
        log.debug('Mode config: %s', mode_config)
        self.mode_config = mode_config
        self.container_map = dict()
        self.analyzer = Analyzer()
        self.analyzer.set_mode(mode_config)

    def _detect_contenders(self, con: Container, resource: ContendedResource):
        contenders = []
        if resource == ContendedResource.UNKN:
            return contenders

        resource_delta_max = -np.Inf
        contender_id = None
        for cid, container in self.container_map.items():
            delta = 0
            if con.cid == container.cid:
                continue
            if resource == ContendedResource.LLC:
                delta = container.get_llcoccupany_delta()
            elif resource == ContendedResource.MEMORY_BW:
                delta = container.get_latest_mbt()
            elif resource == ContendedResource.TDP:
                delta = container.get_freq_delta()

            if delta > 0 and delta > resource_delta_max:
                resource_delta_max = delta
                contender_id = container.cid

        if contender_id:
            contenders.append(contender_id)

        return contenders

    def _append_anomaly(self, anomalies, res, cid, contenders, owca_metrics):
        anomaly = ContentionAnomaly(
                resource=res,
                contended_task_id=cid,
                contending_task_ids=contenders,
                metrics=owca_metrics
            )
        anomalies.append(anomaly)

    def _detect_one_task(self, con: Container, app: str):
        anomalies = []
        if not con.get_metrics():
            return anomalies

        analyzer = self.analyzer
        cid = con.cid
        if app in analyzer.threshold:
            thresh = analyzer.threshold[app]['thresh']
            contends, owca_metrics = con.contention_detect(thresh)
            log.debug('cid=%r contends=%r', cid, contends)
            log.debug('cid=%r threshold metrics=%r', cid, owca_metrics)
            for contend in contends:
                contenders = self._detect_contenders(con, contend)
                self._append_anomaly(anomalies, contend, cid, contenders,
                                     owca_metrics)
            thresh_tdp = analyzer.threshold[app]['tdp']
            tdp_contend, owca_metrics = con.tdp_contention_detect(thresh_tdp)
            if tdp_contend:
                contenders = self._detect_contenders(con, tdp_contend)
                self._append_anomaly(anomalies, tdp_contend, cid, contenders,
                                     owca_metrics)

        return anomalies

    def _get_container_from_taskid(self, cid):
        if cid in self.container_map:
            container = self.container_map[cid]
        else:
            container = Container(cid)
            self.container_map[cid] = container
        return container

    def _remove_finished_tasks(self, cidset: set):
        for cid in self.container_map.copy():
            if cid not in cidset:
                del self.container_map[cid]

    def _cid_to_app(self, cid, tasks_labels: TasksLabels):
        if 'application' in tasks_labels[cid]:
            return tasks_labels[cid]['application']

        return None

    def _is_be_app(self, cid, tasks_labels: TasksLabels):
        if 'type' in tasks_labels[cid] and tasks_labels[cid]['type'] == 'best_efforts':
            return True

        return False

    def _get_headroom_metrics(self, assign_cpus, lcutil, sysutil):
        util_max = self.analyzer.threshold['lcutilmax']
        if util_max < lcutil:
            self.analyzer.threshold['lcutilmax'] = lcutil
            util_max = lcutil
        capacity = assign_cpus * 100
        return [OwcaMetric(name=Metric.LCCAPACITY, value=capacity),
                OwcaMetric(name=Metric.LCMAX, value=util_max),
                OwcaMetric(name=Metric.SYSUTIL, value=sysutil)]

    def _get_threshold_metrics(self):
        """Encode threshold objects as OWCA metrics.
        In contrast to *_threshold metrics from Container,
        all utilization partitions are exposed for all workloads.
        """
        metrics = []
        # Only when debugging is enabled.
        if log.getEffectiveLevel() == logging.DEBUG:
            for cid, threshold in self.analyzer.threshold.items():
                if cid == 'lcutilmax':
                    metrics.append(
                        OwcaMetric(name='threshold_lcutilmax', value=threshold)
                    )
                    continue
                if 'tdp' in threshold and 'bar' in threshold['tdp']:
                    metrics.extend([
                        OwcaMetric(
                            name='threshold_tdp_bar',
                            value=threshold['tdp']['bar'],
                            labels=dict(cid=cid)),
                        OwcaMetric(
                            name='threshold_tdp_util',
                            value=threshold['tdp']['util'],
                            labels=dict(cid=cid)),
                    ])
                if 'thresh' in threshold:
                    for d in threshold['thresh']:
                        metrics.extend([
                            OwcaMetric(
                                name='threshold_cpi',
                                labels=dict(start=str(int(d['util_start'])),
                                            end=str(int(d['util_end'])), cid=cid),
                                value=d['cpi']),
                            OwcaMetric(
                                name='threshold_mpki',
                                labels=dict(start=str(int(d['util_start'])),
                                            end=str(int(d['util_end'])), cid=cid),
                                value=(d['mpki'])),
                            OwcaMetric(
                                name='threshold_mb',
                                labels=dict(start=str(int(d['util_start'])),
                                            end=str(int(d['util_end'])), cid=cid),
                                value=(d['mb'])),
                        ])

        return metrics

    def detect(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels):
        log.debug('prm detect called...')
        log.debug('task_labels=%r', tasks_labels)
        assigned_cpus = 0
        for cid, resources in tasks_resources.items():
            if not self._is_be_app(cid, tasks_labels):
                assigned_cpus += resources['cpus']
            if self.mode_config == ContentionDetector.COLLECT_MODE:
                app = self._cid_to_app(cid, tasks_labels)
                if app:
                    self.analyzer.add_workload_meta(app, resources)

        metric_list = []
        metric_list.extend(self._get_threshold_metrics())
        cidset = set()
        sysutil = 0
        lcutil = 0
        for cid, measurements in tasks_measurements.items():
            app = self._cid_to_app(cid, tasks_labels)
            cidset.add(cid)
            container = self._get_container_from_taskid(cid)
            container.update_measurement(platform.timestamp, measurements)
            metrics = container.get_metrics()
            log.debug('cid=%r container metrics=%r', cid, metrics)
            if metrics:
                if not self._is_be_app(cid, tasks_labels):
                    lcutil += metrics[Metric.UTIL]
                sysutil += metrics[Metric.UTIL]
                owca_metrics = container.get_owca_metrics(app)
                metric_list.extend(owca_metrics)

                if self.mode_config == ContentionDetector.COLLECT_MODE:
                    if 'name' not in tasks_labels[cid]:
                        name = ''
                    else:
                        name = tasks_labels[cid]['name']
                    self.analyzer.add_workload_data(
                        self._cid_to_app(cid, tasks_labels), name,
                        metrics)

        self._remove_finished_tasks(cidset)

        anomaly_list = []
        if self.mode_config == ContentionDetector.DETECT_MODE:
            metric_list.extend(self._get_headroom_metrics(
                assigned_cpus, lcutil, sysutil))
            for container in self.container_map.values():
                app = self._cid_to_app(container.cid, tasks_labels)
                if app:
                    anomalies = self._detect_one_task(container, app)
                    anomaly_list.extend(anomalies)
        elif self.mode_config == ContentionDetector.COLLECT_MODE:
            self.analyzer.add_lc_util(platform.timestamp, lcutil)
        if anomaly_list:
            log.debug('anomalies: %r', anomaly_list)
        if metric_list:
            log.debug('metrics: %r', metric_list)
        return anomaly_list, metric_list
