window.WebApp.factory('cookies', ['$rootScope', '$browser', ($rootScope, $browser) ->
  {
  get: ((key) ->
    key = key + "="
    for c in document.cookie.split(';')
      c = c.substring(1, c.length) while c.charAt(0) is ' '
      return c.substring(key.length, c.length) if c.indexOf(key) == 0
    return null
  ),
  set: ((key, value, expires) ->
    expires = expires ? 3600
    secure = if window.isSecure then ';secure' else ''
    now = new Date()
    time = now.getTime()
    time += expires * 1000
    now.setTime(time)
    # Delete cookie if value is empty, used for logout
    if value != ''
      c_value=escape(value) + "; expires=" + now.toUTCString()
      document.cookie = key + "=" + c_value + secure
    else
      document.cookie = key + "=; expires=Thu, 01-Jan-70 00:00:01 GMT;"
    return null
  )
  }
])