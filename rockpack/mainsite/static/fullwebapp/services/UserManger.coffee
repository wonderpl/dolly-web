window.WebApp.factory('UserManager', ['cookies', '$http', '$q', (cookies, $http, $q) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  @refresh_token = cookies.get('refresh_token')
  @user_id = cookies.get('user_id')
  @access_token = cookies.get('access_token')

  User = {
    details: {}
    timeOfLastRefresh: null

    refreshToken: (refreshToken) ->
      $http({
        method: 'POST',
        data: $.param({refresh_token: refreshToken, grant_type: 'refresh_token'}),
        url: window.apiUrls['refresh_token'],
        headers: headers
      })
      .success((data) =>
          @TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)
          @details = data
          cookies.set("access_token", data.access_token, data.expires)
      )
      .error((data) =>
        console.log data
      )

    Login: (username, password) ->
      OAuth.login(username, password)
      .success((data) =>
          @details = data
      )
      .error((data) =>
        console.log data
      )

    getTimeToNextRefresh: () ->

    TriggerRefresh: (timeToRefresh, token) ->
      window.setTimeout((() => @refreshToken(token)) ,timeToRefresh)
      timeOfLastRefresh =

  }

  deferred = $q.defer()

  if @refresh_token?
    console.log 'We have a refresh token (lets relog)'
    User.refreshToken(@refresh_token)
    .success((data) =>
      console.log ("refresh token success")
      deferred.resolve(User)
    )
    .error((data) =>
      console.log ("Refresh fails, token might no longer be valid")
      console.log (data)
    )
  else
    console.log ("no user cradentials avilable, redirecting to login")
    $location.path("/login").replace()

  return deferred.promise

])