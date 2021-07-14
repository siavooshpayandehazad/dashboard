

async function isLoggedIn () {
  const token = localStorage.getItem('token')
  if (!token) return false
  return true
}

async function autoRedirect () {
  const validLogin = await isLoggedIn()
  if (!validLogin)
    if(window.location.pathname !== '/home')
      window.location.replace('/home')
}

function logout(){
  localStorage.setItem('token',"false")
  //window.location.replace('/home')
  checkLoggedIn();
}
autoRedirect();

function togglePassword() {
  var x = document.getElementById("password");
  if (x.type === "password") {
    x.type = "text";
  } else {
    x.type = "password";
  }
}

function login(){
  var password = document.getElementById("password").value;
   document.getElementById("password").value = "";
  $.ajax({
      type: "POST",
      url: "/home",
      data: {"type":"password", "value": password},
  }).success(function(result){
    if (result == "success"){
      localStorage.setItem('token',"true");
      document.getElementById("overlay").style.display = "none";
      document.getElementById("password").style.backgroundColor = "white";
    }
    else{
      document.getElementById("password").style.backgroundColor = "#fc9272";
    }
  })
}

function checkLoggedIn () {
  const token = localStorage.getItem('token');
  if ((token !== "true")){
    document.getElementById("overlay").style.display = "block";
  }
}

checkLoggedIn();
