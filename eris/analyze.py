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

""" This module implements platform metrics data analysis. """

from __future__ import print_function
from __future__ import division

import argparse
import pandas as pd
from container import Container, Contention
from eris import remove_finished_containers, detect_contender, init_data_file
from analyze.analyzer import Analyzer, ThreshType, Metric


def process_one_node(args, ndf, analyzer):
    metric_cons = dict()
    cpu_model = ndf['cpu_model'].values[0]
    key = 'cid' if args.key_cid else 'name'
    times = ndf['time'].unique()
    times.sort(axis=0)
    for time in times:
        pdata = ndf[ndf['time'] == time]
        cids = pdata[key].unique()
        remove_finished_containers(cids, metric_cons)
        for cid in cids:
            jdata = pdata[pdata[key] == cid]
            name = jdata['name'].values[0]
            ncpu = str(jdata['vcpu_count'].values[0])
            thresh = analyzer.get_thresh(cpu_model, ncpu, name, ThreshType.METRICS)
            tdp_thresh = analyzer.get_thresh(cpu_model, ncpu, name, ThreshType.TDP)
            if cid in metric_cons:
                con = metric_cons[cid]
            else:
                con = Container('cgroupfs', cid, name, [], args.verbose, thresh,
                                tdp_thresh)
                metric_cons[cid] = con
            for row_tuple in jdata.iterrows():
                con.update_metrics(row_tuple)

        for cid in cids:
            con = metric_cons[cid]
            contend_res = con.contention_detect()
            tdp_contend = con.tdp_contention_detect()
            if tdp_contend:
                contend_res.append(tdp_contend)
            for contend in contend_res:
                if contend != Contention.UNKN:
                    detect_contender(metric_cons, contend, con)
                else:
                    metrics = con.metrics
                    with open('contention.csv', 'a') as contf:
                        contf.write(metrics['time'] + ',' + con.node + ',' + con.cid + ',' + con.name + ',' + str(contend) + ',' + ','
                        + str(con.utils) + ',' + str(metrics[Metric.CPI]) + ',' + str(metrics[Metric.L3MPKI]) + ',' + str(metrics[Metric.MSPKI]) + ','
                        + str(metrics[Metric.MB]) + ',' + str(metrics[Metric.NF]) + '\n')


def process_offline_data(args, analyzer):
    """
    General procedure of offline analysis
        args - arguments from command line input
    """
    cols = ['time', 'machine', 'cid', 'name', 'type', 'contender', Metric.UTIL, Metric.CPI, Metric.L3MPKI, Metric.MSPKI, Metric.MB, Metric.NF]
    init_data_file('contention.csv', cols, args.verbose)
    mdf = pd.read_csv(args.metric_file)
    nodes = mdf['machine'].unique()
    for node in nodes:
        ndf = mdf[mdf['machine'] == node]
        process_one_node(args, ndf, analyzer)        
    
def process(args):
    """
    General procedure of analysis
        args - arguments from command line input
    """
    analyzer = Analyzer(args.workload_conf_file)
    if args.offline:
        process_offline_data(args, analyzer)
    else:
        strict = True if args.fense_type == 'gmm-strict' else False
        use_origin = True if args.fense_method == 'gmm-origin' else False
        analyzer.build_model(args.util_file, args.metric_file, args.ratio_min,
                             args.thresh, args.prob_thresh, strict, use_origin, args.verbose)

def main():
    """ Script entry point. """
    parser = argparse.ArgumentParser(description='This tool analyzes CPU\
                                     utilization and platform metrics\
                                     collected from eris agent and build data\
                                     model for contention detect and resource\
                                     regulation.')
    parser.add_argument('workload_conf_file', help='workload configuration\
                        file describes each task name, type, request cpu\
                        count', type=argparse.FileType('rt'),
                        default='workload.json')
    parser.add_argument('-v', '--verbose', help='increase output verbosity',
                        action='store_true')
    parser.add_argument('-t', '--thresh', help='span threshold used in outlier\
                        detection', type=int, default=3)
    parser.add_argument('-p', '--prob-thresh', help='probility threshold used in outlier\
                        detection', type=float, default=0.05)
    parser.add_argument('-r', '--ratio-min', help='quota ratio for minimal utilization bin\
                        detection', type=float, default=0.3)
    parser.add_argument('-a', '--fense-method', help='fense method used in outlier\
                        detection', choices=['gmm-origin', 'gmm-standard'],
                        default='gmm-standard')
    parser.add_argument('-f', '--fense-type', help='fense type used in outlier\
                        detection', choices=['gmm-strict', 'gmm-normal'],
                        default='gmm-strict')
    parser.add_argument('-m', '--metric-file', help='metrics file collected\
                        from eris agent', type=argparse.FileType('rt'),
                        default=Analyzer.METRIC_FILE )
    parser.add_argument('-u', '--util-file', help='Utilization file collected\
                        from eris agent', type=argparse.FileType('rt'),
                        default=Analyzer.UTIL_FILE)
    parser.add_argument('-o', '--offline', help='do offline analysis based on\
                        given metrics file', action='store_true')
    parser.add_argument('-i', '--key-cid', help='use container id in workload\
                        configuration file as key id', action='store_true')

    args = parser.parse_args()
    if args.verbose:
        print(args)

    process(args)

if __name__ == '__main__':
    main()
