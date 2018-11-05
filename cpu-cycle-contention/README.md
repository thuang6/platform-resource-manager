# CPU Cycle Contention Detector

CPU Cycle Contention Detector detects contention base on the utilization of containers.

## Requirements

- Golang compiler

## How to Run
```
go run main.go [-p port]
```
Visit 127.0.0.1:port (default is 8888) and upload example.csv

## CSV format
Columns
- Timestamp
- Container 0
- Container 1
- ...