# CPU Cycle Contention Detector

The CPU Cycle Contention Detector detects contention based on the utilization of containers.

## Prerequisites

* Golang compiler

## How to run

Use the command:

```
go run main.go [-p port]
```
Visit 127.0.0.1:port (default is 8888) and upload the `example.csv` file.

## CSV format

The columns use the following format:

* Timestamp
* Container 0
* Container 1
* ...