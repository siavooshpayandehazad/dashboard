

function shutdown(){
  $.ajax({ type: "POST",
      url: "http://"+window.location.hostname+":5000/shutdown"
  });
  logout();
}