const zeroPad = (num, places) => String(num).padStart(places, '0')
function goToMonth(year, i){
  page=window.location.href;
  window.location.href=page.split('?')[0]+"?date="+year+"-"+zeroPad(i+1, 2)+"-01"
}
