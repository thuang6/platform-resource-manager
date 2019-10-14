#! /bin/bash
cur_dir=`pwd`
echo 'time,cid,name,cpu_model,vcpu_count,cycle,instruction,cache_miss,cache_occupancy,memory_bandwidth_total,cycles_per_instruction,cache_miss_per_kilo_instruction,normalized_frequency,cpu_utilization,stalls_memory_load_per_kilo_instruction,machine' > $cur_dir/metrics_merged.csv
for element in `ls $1`
    do
        dir_or_file=$cur_dir/$1/$element
        if [ -d $dir_or_file ]
        then
           if [ -r $dir_or_file/metric.csv ]
           then
               echo $dir_or_file
               machine=`echo "\"$element\""`
               cat $dir_or_file/metric.csv | tail -n +2 | awk 'BEGIN{FS=OFS=","}{print $0 OFS '$machine'}' >> $cur_dir/metrics_merged.csv
               python merge.py $dir_or_file/workload.json
           fi
        fi
    done

#jq -s '.[]' workload-merged.json > workload.json
#rm workload-merged.json
