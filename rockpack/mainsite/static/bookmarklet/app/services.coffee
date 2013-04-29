window.Bookmarklet.factory('cookies', ['$rootScope', '$browser', ($rootScope, $browser) ->
  {
    get: ((key) ->
      key = key + "="
      for c in document.cookie.split(';')
        c = c.substring(1, c.length) while c.charAt(0) is ' '
        return c.substring(key.length, c.length) if c.indexOf(key) == 0
      return null
    ),
    set: ((key, value, expires) ->
      secure = if window.isSecure then ';secure' else ''
      now = new Date()
      time = now.getTime()
      time += expires * 1000
      now.setTime(time)
      c_value=escape(value) + "; expires=" + now.toUTCString()
      document.cookie = key + "=" + c_value + secure
      return null
    )
  }
])