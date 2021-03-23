#!/bin/bash
date=$(date '+%Y-%m-%d %H:%M:%S')
today=$(date +"%d-%m-%y")

CPUReportDir="/home/pi/dashboard/serverScripts/reports/cpuReports"
GPUReportDir="/home/pi/dashboard/serverScripts/reports/gpuReports"


cpu=$(mpstat | grep -A 1 "idle" | tail -n 1)
OUTFILE="$CPUReportDir/cpuUsageData_$today.txt"
echo $cpu >> $OUTFILE

cpuTemp=$(cat /sys/class/thermal/thermal_zone0/temp)
OUTFILE="$CPUReportDir/cpuTempData_$today.txt"
echo $cpuTemp $date >> $OUTFILE

temp=$(vcgencmd measure_temp)
OUTFILE="$GPUReportDir/gpuTempData_$today.txt"
echo $temp $date >> $OUTFILE
