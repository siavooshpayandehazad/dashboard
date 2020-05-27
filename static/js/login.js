

async function isLoggedIn () {
  const token = localStorage.getItem('token')
  if (!token) return false
  return true
}

async function autoRedirect () {
  const validLogin = await isLoggedIn()
  if (!validLogin)
    window.location.replace('/home')
}

function logout(){
  localStorage.setItem('token',"false")
  window.location.replace('/home')
}
autoRedirect();
