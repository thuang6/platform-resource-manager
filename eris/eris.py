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

""" This module implements resource monitor and control agent """

from __future__ import print_function
from __future__ import division

import os
import sys

import subprocess
import time
import traceback

import docker
import numpy as np
import pandas as pd

from argparse import ArgumentParser, FileType
from datetime import datetime
try:
    from os import cpu_count
except ImportError:
    from multiprocessing import cpu_count
from threading import Thread

from container import Container, Contention
from cpuquota import CpuQuota
from llcoccup import LlcOccup
from mresource import Resource
from naivectrl import NaiveController
from prometheus import PrometheusClient


__version__ = 0.8


class Context(object):
    """ This class encapsulate all configuration and args """

    def __init__(self):
        self._docker_client = None
        self._prometheus = None

        self.shutdown = False
        self.args = None
        self.sysmax_file = 'lcmax.txt'
        self.sysmax_util = 0
        self.lc_set = {}
        self.be_set = {}
        self.cpuq = None
        self.llc = None
        self.controllers = {}
        self.util_cons = dict()
        self.metric_cons = dict()
        self.thresh_map = None
        self.tdp_thresh_map = None
        self.cgroup_driver = 'cgroupfs'

    @property
    def docker_client(self):
        if self._docker_client is None:
            self._docker_client = docker.from_env(version='auto')
        return self._docker_client

    @property
    def prometheus(self):
        if self._prometheus is None:
            self._prometheus = PrometheusClient()
        return self._prometheus


def each_container_pgos_metric(lines, delim='\t'):
    metric_mappings = {
        'cycles': ('CYC', int),
        'instructions': ('INST', int),
        'LLC misses': ('L3MISS', int),
        'stalls L2 miss': ('L2STALL', int),
        'stalls memory load': ('MEMSTALL', int),
        'LLC occupancy': ('L3OCC', int),
        'Memory bandwidth local': ('MBL', float),
        'Memory bandwidth remote': ('MBR', float),
    }

    for line in lines:
        items = line.split(delim)
        if len(items) < 4:
            continue
        cid, metric_name, timestamp, val = items[:4]
        if metric_name in metric_mappings:
            name, converter = metric_mappings[metric_name]
            yield cid, {name: converter(val)}, int(timestamp)


def detect_contender(metric_cons, contention_type, container_contended):
    resource_delta_max = -np.Inf
    suspect = "unknown"

    for cid, container in metric_cons.items():
        delta = 0
        if cid == container_contended.cid:
            continue
        if contention_type == Contention.LLC:
            delta = container.get_llcoccupany_delta()
        elif contention_type == Contention.MEM_BW:
            delta = container.get_latest_mbt()
        elif contention_type == Contention.TDP:
            delta = container.get_freq_delta()

        if delta > 0 and delta > resource_delta_max:
            resource_delta_max = delta
            suspect = container.name

        print('Contention %s for container %s: Suspect is %s' %
              (contention_type, container_contended.name, suspect))


def set_metrics(ctx, data):
    """
    This function collect metrics from pgos tool and trigger resource
    contention detection and control
        ctx - agent context
        data - metrics data collected from pgos
    """
    timestamp = datetime.now()

    for cid, metric, _ in each_container_pgos_metric(data):
        container = ctx.metric_cons[cid]
        container.metrics.update(metric)

    contention = {
        Contention.LLC: False,
        Contention.MEM_BW: False,
        Contention.UNKN: False
    }
    contention_map = {}
    bes = []
    lcs = []
    findbe = False
    for cid, con in ctx.metric_cons.items():
        key = con.cid if ctx.args.key_cid else con.name

        if key in ctx.lc_set:
            if ctx.args.exclusive_cat:
                lcs.append(con)
            con.update_cpu_usage()
            metrics = con.get_metrics()
            if metrics:
                metrics['TIME'] = timestamp
                if metrics['INST'] == 0:
                    metrics['CPI'] = 0
                    metrics['L3MPKI'] = 0
                    metrics['L2SPKI'] = 0
                    metrics['MSPKI'] = 0
                else:
                    metrics['CPI'] = metrics['CYC'] / metrics['INST']
                    metrics['L3MPKI'] = metrics['L3MISS'] * 1000 /\
                        metrics['INST']
                    metrics['L2SPKI'] = metrics['L2STALL'] * 1000 /\
                        metrics['INST']
                    metrics['MSPKI'] = metrics['MEMSTALL'] * 1000 /\
                        metrics['INST']
                if con.utils == 0:
                    metrics['NF'] = 0
                else:
                    metrics['NF'] = int(metrics['CYC'] /
                                        ctx.args.metric_interval /
                                        10000 / con.utils)
                if ctx.args.detect:
                    con.update_metrics_history()

                if ctx.args.record:
                    with open('./metrics.csv', 'a') as metricf:
                        metricf.write(str(con))

                    if ctx.args.enable_prometheus:
                        ctx.prometheus.send_metrics(con.name, con.utils,
                                                    metrics['CYC'],
                                                    metrics['L3MISS'],
                                                    metrics['INST'],
                                                    metrics['NF'],
                                                    metrics['MBR'] +
                                                    metrics['MBL'],
                                                    metrics['L3OCC'], 0)

                if ctx.args.detect:
                    contend_res = con.contention_detect()
                    if_contended = False

                    if contend_res:
                        if_contended = True
                        for contend in contend_res:
                            contention[contend] = True

                    tdp_contend = con.tdp_contention_detect()
                    if tdp_contend is not None:
                        if_contended = True
                        contention[tdp_contend] = True

                    if if_contended:
                        contention_map[con] = contention.copy()

        if key in ctx.be_set:
            findbe = True
            bes.append(con)

    if ctx.args.detect:
        for container_contended, contention_list in contention_map.items():
            for contention_type, contention_type_if_happened\
                    in contention_list.items():
                if contention_type_if_happened and\
                   contention_type != Contention.UNKN:
                    detect_contender(ctx.metric_cons, contention_type,
                                     container_contended)
    if findbe and ctx.args.control:
        for contention, flag in contention.items():
            if contention in ctx.controllers:
                ctx.controllers[contention].update(bes, lcs, flag, False)


def remove_finished_containers(cids, consmap):
    """
    remove finished containers from cached container map
        cids - container id list from docker
        mon_cons - cached container map
    """
    for cid in consmap.copy():
        if cid not in cids:
            del consmap[cid]


def list_pids(container):
    """
    list all process id of one container
        container - container object listed from Docker
    """
    procs = container.top()['Processes']
    pids = [pid[1] for pid in procs] if procs else []
    return [tid for pid in pids
            for tid in os.listdir('/proc/' + pid + '/task')] if pids else []


def mon_util_cycle(ctx):
    """
    CPU utilization monitor timer function
        ctx - agent context
    """
    findbe = False
    lc_utils = 0
    be_utils = 0
    date = datetime.now().isoformat()
    bes = []
    newbe = False
    containers = ctx.docker_client.containers.list()
    remove_finished_containers({c.id for c in containers}, ctx.util_cons)

    for container in containers:
        cid = container.id
        name = container.name
        pids = list_pids(container)
        key = cid if ctx.args.key_cid else name
        if cid in ctx.util_cons:
            con = ctx.util_cons[cid]
        else:
            con = Container(ctx.cgroup_driver, cid, name, pids,
                            ctx.args.verbose)
            ctx.util_cons[cid] = con
            if ctx.args.control:
                if key in ctx.be_set:
                    newbe = True
                    ctx.cpuq.set_share(con, CpuQuota.CPU_SHARE_BE)
                else:
                    ctx.cpuq.set_share(con, CpuQuota.CPU_SHARE_LC)
        con.update_cpu_usage()
        if ctx.args.record:
            with open('./util.csv', 'a') as utilf:
                utilf.write(date + ',' + cid + ',' + name +
                            ',' + str(con.utils) + '\n')

        if key in ctx.lc_set:
            lc_utils = lc_utils + con.utils

        if key in ctx.be_set:
            findbe = True
            be_utils = be_utils + con.utils
            bes.append(con)

    loadavg = os.getloadavg()[0]
    if ctx.args.record:
        with open('./util.csv', 'a') as utilf:
            utilf.write(date + ',,lcs,' + str(lc_utils) + '\n')
            utilf.write(date + ',,loadavg1m,' + str(loadavg) + '\n')

    if lc_utils > ctx.sysmax_util:
        update_sysmax(ctx, lc_utils)
        if ctx.args.control:
            ctx.cpuq.update_max_sys_util(lc_utils)

    if newbe:
        ctx.cpuq.budgeting(bes, [])

    if findbe and ctx.args.control:
        exceed, hold = ctx.cpuq.detect_margin_exceed(lc_utils, be_utils)
        if not ctx.args.enable_hold:
            hold = False
        ctx.controllers[Contention.CPU_CYC].update(bes, [], exceed, hold)


def mon_metric_cycle(ctx):
    """
    Platform metrics monitor timer function
        ctx - agent context
    """
    containers = ctx.docker_client.containers.list()
    cgroups = []
    cids = []
    bes = []
    lcs = []
    newcon = False
    newbe = False
    remove_finished_containers({c.id for c in containers}, ctx.metric_cons)

    for container in containers:
        cid = container.id
        name = container.name
        pids = list_pids(container)
        key = cid if ctx.args.key_cid else name
        if cid in ctx.metric_cons:
            con = ctx.metric_cons[cid]
            con.update_pids(pids)
        else:
            thresh = ctx.thresh_map.get(key, [])
            tdp_thresh = ctx.tdp_thresh_map.get(key, [])
            con = Container(ctx.cgroup_driver, cid, name, pids,
                            ctx.args.verbose, thresh, tdp_thresh)
            ctx.metric_cons[cid] = con
            con.update_cpu_usage()
            if ctx.args.control and not ctx.args.disable_cat:
                newcon = True
                if key in ctx.be_set:
                    newbe = True
        if key in ctx.lc_set:
            if ctx.args.exclusive_cat:
                lcs.append(con)
            cids.append(cid)
            cgroups.append('/sys/fs/cgroup/perf_event/' +
                           con.parent_path + con.con_path)
        if key in ctx.be_set:
            bes.append(con)
    if newbe or newcon and bes and ctx.args.exclusive_cat:
        ctx.llc.budgeting(bes, lcs)

    if cgroups:
        period = str(ctx.args.metric_interval - 2)
        args = [
            './pgos',
            '-cids', ','.join(cids),
            '-cgroup', ','.join(cgroups),
            '-period', period,
            '-frequency', period,
            '-cycle', '1',
            '-core', str(cpu_count()),
        ]
        if ctx.args.verbose:
            print(' '.join(args))
        output = subprocess.check_output(args, stderr=subprocess.STDOUT)
        data = output.decode('utf-8').splitlines()
        if ctx.args.verbose:
            print(output.decode('utf-8'))
        set_metrics(ctx, data)


def monitor(func, ctx, interval):
    """
    wrap schedule timer function
        ctx - agent context
        interval - timer interval
    """
    next_time = time.time()
    while not ctx.shutdown:
        func(ctx)
        while True:
            next_time += interval
            delta = next_time - time.time()
            if delta > 0:
                break
        time.sleep(delta)


def init_threshbins(jdata):
    """
    Initialize thresholds in all bins for one workload
        jdata - thresholds data for one workload
    """
    key_mappings = [
        ('util_start', 'UTIL_START'),
        ('util_end', 'UTIL_END'),
        ('cpi', 'CPI_THRESH'),
        ('mpki', 'MPKI_THRESH'),
        ('mb', 'MB_THRESH'),
        ('l2spki', 'L2SPKI_THRESH'),
        ('mspki', 'MSPKI_THRESH'),
    ]
    return [
        {
            from_key: row_tuple[1][to_key]
            for from_key, to_key in key_mappings
        }
        for row_tuple in jdata.iterrows()
    ]


def init_tdp_map(args):
    """
    Initialize thresholds for TDP contention for all workloads
        args - agent command line arguments
    """
    tdp_file = args.tdp_file if hasattr(args, 'tdp_file')\
        and args.tdp_file else 'tdp_thresh.csv'
    tdp_df = pd.read_csv(tdp_file)
    key = 'CID' if args.key_cid else 'CNAME'
    cids = tdp_df[key].unique()
    thresh_map = {}
    for cid in cids:
        tdpdata = tdp_df[tdp_df[key] == cid]

        for row_turple in tdpdata.iterrows():
            row = row_turple[1]
            thresh = dict()
            thresh['util'] = row['UTIL']
            thresh['mean'] = row['MEAN']
            thresh['std'] = row['STD']
            thresh['bar'] = row['BAR']
            thresh_map[cid] = thresh

    if args.verbose:
        print(thresh_map)
    return thresh_map


def init_threshmap(args):
    """
    Initialize thresholds for other contentions for all workloads
        args - agent command line arguments
    """
    thresh_file = args.thresh_file if hasattr(args, 'thresh_file')\
        and args.thresh_file else 'thresh.csv'
    thresh_df = pd.read_csv(thresh_file)
    key = 'CID' if args.key_cid else 'CNAME'
    cids = thresh_df[key].unique()
    thresh_map = {}
    for cid in cids:
        jdata = thresh_df[thresh_df[key] == cid].sort_values('UTIL_START')
        bins = init_threshbins(jdata)
        thresh_map[cid] = bins

    if args.verbose:
        print(thresh_map)
    return thresh_map


def init_wlset(ctx):
    """
    Initialize workload set for both LC and BE
        ctx - agent context
    """
    key = 'CID' if ctx.args.key_cid else 'CNAME'
    wl_df = pd.read_csv(ctx.args.workload_conf_file)
    lcs = []
    bes = []
    for row_turple in wl_df.iterrows():
        row = row_turple[1]
        workload = row[key]
        if row['TYPE'] == 'LC':
            lcs.append(workload)
        else:
            bes.append(workload)
    ctx.lc_set = set(lcs)
    ctx.be_set = set(bes)
    if ctx.args.verbose:
        print(ctx.lc_set)
        print(ctx.be_set)


def update_sysmax(ctx, lc_utils):
    """
    Update system maximal utilization based on utilization of LC workloads
        ctx - agent context
        lc_utils - monitored LC workload utilization maximal value
    """
    ctx.sysmax_util = int(lc_utils)
    subprocess.Popen('echo ' + str(ctx.sysmax_util) + ' > ' + ctx.sysmax_file,
                     shell=True)


def init_sysmax(ctx):
    """
    Initialize historical system maximal utilization from model file
        ctx - agent context
    """
    try:
        with open(ctx.sysmax_file, 'r') as f:
            ctx.sysmax_util = int(f.read().strip())
    except (IOError, ValueError):
        ctx.sysmax_util = cpu_count() * 100
    if ctx.args.verbose:
        print(ctx.sysmax_util)


def detect_cgroup_driver():
    """
    Detect docker cgroup parent dir based on cgroup driver type
    """
    client = docker.from_env()
    dockinfo = client.info()
    cgroup_driver = dockinfo['CgroupDriver']
    if cgroup_driver != 'cgroupfs':
        print('Unknown cgroup driver: ' + cgroup_driver)

    return cgroup_driver


def parse_arguments():
    """ agent command line arguments parse function """

    parser = ArgumentParser(description='eris agent monitor\
                            container CPU utilization and platform\
                            metrics, detect potential resource\
                            contention and regulate best-efforts\
                            tasks resource usages')
    parser.add_argument('workload_conf_file', help='workload configuration\
                        file describes each task name, type, id, request cpu\
                        count', type=FileType('rt'), default='wl.csv')
    parser.add_argument('-v', '--verbose', help='increase output verbosity',
                        action='store_true')
    parser.add_argument('-g', '--collect-metrics', help='collect platform\
                        performance metrics (CPI, MPKI, etc..)',
                        action='store_true')
    parser.add_argument('-d', '--detect', help='detect resource contention\
                        between containers', action='store_true')
    parser.add_argument('-c', '--control', help='regulate best-efforts task\
                        resource usages', action='store_true')
    parser.add_argument('-r', '--record', help='record container CPU\
                        utilizaton and platform metrics in csv file',
                        action='store_true')
    parser.add_argument('-i', '--key-cid', help='use container id in workload\
                        configuration file as key id', action='store_true')
    parser.add_argument('-e', '--enable-hold', help='keep container resource\
                        usage in current level while the usage is close but\
                        not exceed throttle threshold ', action='store_true')
    parser.add_argument('-n', '--disable-cat', help='disable CAT control while\
                        in resource regulation', action='store_true')
    parser.add_argument('-w', '--exclusive-cat', help='use exclusive CAT control while\
                        in resource regulation', action='store_true')
    parser.add_argument('-p', '--enable-prometheus', help='allow eris send\
                        metrics to Prometheus', action='store_true')
    parser.add_argument('-u', '--util-interval', help='CPU utilization monitor\
                        interval', type=int, choices=range(1, 10), default=2)
    parser.add_argument('-m', '--metric-interval', help='platform metrics\
                        monitor interval', type=int, choices=range(5, 60),
                        default=20)
    parser.add_argument('-l', '--llc-cycles', help='cycle number in LLC\
                        controller', type=int, default=6)
    parser.add_argument('-q', '--quota-cycles', help='cycle number in CPU CFS\
                        quota controller', type=int, default=7)
    parser.add_argument('-k', '--margin-ratio', help='margin ratio related to\
                        one logical processor used in CPU cycle regulation',
                        type=float, default=0.5)
    parser.add_argument('-t', '--thresh-file', help='threshold model file build\
                        from analyze.py tool', type=FileType('rt'))
    parser.add_argument('-x', '--tdp-file', help='TDP threshold model file build\
                        from analyze.py tool', type=FileType('rt'))

    args = parser.parse_args()
    if args.verbose:
        print(args)
    return args


def main():
    """ Script entry point. """
    ctx = Context()
    ctx.args = parse_arguments()
    ctx.cgroup_driver = detect_cgroup_driver()
    init_wlset(ctx)
    init_sysmax(ctx)

    if ctx.args.enable_prometheus:
        ctx.prometheus.start()

    if ctx.args.detect:
        ctx.thresh_map = init_threshmap(ctx.args)
        ctx.tdp_thresh_map = init_tdp_map(ctx.args)

    if ctx.args.control:
        ctx.cpuq = CpuQuota(ctx.sysmax_util, ctx.args.margin_ratio,
                            ctx.args.verbose)
        quota_controller = NaiveController(ctx.cpuq, ctx.args.quota_cycles)
        ctx.llc = LlcOccup(Resource.BUGET_LEV_MIN, ctx.args.exclusive_cat)
        llc_controller = NaiveController(ctx.llc, ctx.args.llc_cycles)
        if ctx.args.disable_cat:
            ctx.llc = LlcOccup(Resource.BUGET_LEV_FULL, exclusive=False)
            ctx.controllers = {Contention.CPU_CYC: quota_controller}
        else:
            ctx.controllers = {Contention.CPU_CYC: quota_controller,
                               Contention.LLC: llc_controller}
    if ctx.args.record:
        with open('./util.csv', 'w') as utilf:
            utilf.write('TIME,CID,CNAME,UTIL\n')

    threads = [Thread(target=monitor, args=(mon_util_cycle,
                                            ctx, ctx.args.util_interval))]

    if ctx.args.collect_metrics:
        if ctx.args.record:
            with open('./metrics.csv', 'w') as metricf:
                print('TIME,CID,CNAME,INST,CYC,CPI,L3MPKI,L3MISS,NF,UTIL,L3OCC,\
MBL,MBR,L2STALL,MEMSTALL,L2SPKI,MSPKI', file=metricf)
        threads.append(Thread(target=monitor,
                              args=(mon_metric_cycle,
                                    ctx, ctx.args.metric_interval)))

    for thread in threads:
        thread.start()

    print('eris agent version', __version__, 'is started!')

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print('Shutdown eris agent ...exiting')
        ctx.shutdown = True
    except Exception:
        traceback.print_exc(file=sys.stdout)

    sys.exit(0)


if __name__ == '__main__':
    main()
