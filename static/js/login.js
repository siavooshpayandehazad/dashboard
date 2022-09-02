function logout(){
  localStorage.setItem('token',"false")
  $.ajax({
      type: "POST",
      url: "/",
      data: {"type":"logout"},
  })
  window.location.replace('/login')
}

function shutdown(){
  $.ajax({ type: "POST",
      url: "http://"+window.location.hostname+":5000/shutdown"
  });
  logout();
}