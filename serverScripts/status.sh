#!/bin/bash
date=$(date '+%Y-%m-%d %H:%M:%S')
today=$(date +"%d-%m-%y")
year=$(date +"%Y")

CPUReportDir="/media/pi/ec83d7d4-47dd-4b33-9fe9-261c1b6700fa/dashboard/serverScripts/reports/cpuReports/$year"
mkdir $CPUReportDir


cpu=$(mpstat | grep -A 1 "idle" | tail -n 1)
OUTFILE="$CPUReportDir/cpuUsageData_$today.txt"
echo $cpu >> $OUTFILE

cpuTemp=$(cat /sys/class/thermal/thermal_zone0/temp)
OUTFILE="$CPUReportDir/cpuTempData_$today.txt"
echo $cpuTemp $date >> $OUTFILE
