date=$(date '+%Y-%m-%d %H:%M:%S')
today=$(date +"%d-%m-%y")

reportDir="reports/cpuReports"
cpu=$(mpstat | grep -A 1 "idle" | tail -n 1)
OUTFILE="$reportDir/cpuUsageData_$today.txt"
echo $cpu >> $OUTFILE


tempReportDir="reports/tempReports"
temp=$(vcgencmd measure_temp)
OUTFILE="$tempReportDir/tempData_$today.txt"
echo $temp+"\t"+$date >> $OUTFILE
