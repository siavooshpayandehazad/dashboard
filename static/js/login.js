

async function isLoggedIn () {
  const token = localStorage.getItem('token')
  if (!token) return false
  return true
}

async function autoRedirect () {
  const validLogin = await isLoggedIn()
  if (!validLogin)
    if(window.location.pathname !== '/')
      window.location.replace('/')
}

function logout(){
  localStorage.setItem('token',"false")
  $.ajax({
      type: "POST",
      url: "/",
      data: {"type":"logout"},
  })
  window.location.replace('/login')
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

