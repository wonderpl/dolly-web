angular.module('WebApp').factory('oauthService', [ '$http', 'apiUrl', 'cookies', '$rootScope', ($http, apiUrl, cookies, $rootScope) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  OAuth = {

    timeOfLastRefresh: null

    credentials: {
      refresh_token: cookies.get('refresh_token'),
      user_id: cookies.get('user_id'),
      access_token: cookies.get('access_token'),
    }

    TriggerRefresh: (timeToRefresh, token) ->
      window.setTimeout((() => @refreshToken(token)) ,timeToRefresh)

    refreshToken: () ->
      $http({
        method: 'POST',
        data: $.param({refresh_token: OAuth.credentials.refresh_token, grant_type: 'refresh_token'}),
        url: apiUrl.refresh_token,
        headers: headers
      })
        .success((data) =>
          @isLoggedIn = true
          cookies.set("access_token", data.access_token, data.expires)
          @credentials = data

          # Trigger next refresh
          @TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)
          @timeOfLastRefresh = (new Date()).getTime()
        )
        .error((data) =>
          console.log data
        )

    Login: (username, password) ->
      $http({
        method: 'POST',
        data: $.param({username: username, password: password, grant_type: 'password'}),
        url: apiUrl.login,
        headers: headers
      })
        .success((data) =>
          OAuth._ApplyLogin(data)
        )
        .error((data) =>
          $rootScope.message.message = 'User Name or Password did not match'
          console.log data
        )

    ExternalLogin: (provider, external_token) ->
      $http({
        method: 'POST',
        data: $.param({'external_system': provider, 'external_token': external_token}),
        url: apiUrl.login_register_external,
        headers: headers
      })
        .success((data) ->
          ApplyLogin(data)
        )
        .error((data)->
          console.log data
        )

    _ApplyLogin: (data) ->
      cookies.set("access_token", data.access_token, data.expires)
      cookies.set("refresh_token", data.refresh_token, 2678400)
      cookies.set("user_id", data.user_id, 2678400)
      @isLoggedIn = true
      @credentials = data
      @TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)


    ###
    Registers a new User
    No user validation - Implemented on the form itself.
    ###

    register: (user) ->
      $http({
        method: 'POST',
        data: $.param(user),
        url: apiUrl.register,
        headers: headers
      })
      .success((data) ->
        OAuth._ApplyLogin(data)
        return data
      )
      .error((data) ->
        return data
      )

    # Accepts Username or Password (supplied as username)
    resetPassword: (username) ->
      $http({
        method: 'POST',
        data: $.param({username: username, grant_type: 'refresh_token'}),
        url: apiUrl.reset_password,
        headers: headers
      })
      .success((data) ->
        return {"status": 'success'}
      )
      .error((data) ->
        console.log data
      )

    # facebook: (external_token) ->
  }

  return OAuth
])