import argparse
import json

def main():
    """ Script entry point. """
    parser = argparse.ArgumentParser(description='This tool merge workload meta from mutiple nodes')
    parser.add_argument('workload_conf_file', help='workload configuration\
                        file describes each task name, type, request cpu\
                        count', type=argparse.FileType('rt'),
                        default='workload.json')
    args = parser.parse_args()
    workload_merged = {}
    try:
        with open('workload-merged.json', 'r') as mf:
            workload_merged = json.loads(mf.read())
    except Exception as e:
        print('cannot read merged workload file - continue')

    try:
        with args.workload_conf_file as wlf:
            workload_meta = json.loads(wlf.read())
    except Exception as e:
        print('cannot read workload file - stopped')
        raise e

    for job in workload_meta:
        if job not in workload_merged:
            workload_merged[job] = workload_meta[job]
    
    print(workload_merged)
    with open('workload-merged.json', 'w') as mf:
        mf.write(json.dumps(workload_merged, indent=4))

if __name__ == '__main__':
    main()