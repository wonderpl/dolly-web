angular.module('WebApp').factory('oauthService', [ '$http', 'apiUrl', 'cookies', '$rootScope', ($http, apiUrl, cookies, $rootScope) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  OAuth = {

    timeOfLastRefresh: null


    RefreshToken: (refreshToken) ->
      $http({
        method: 'POST',
        data: $.param({refresh_token: refreshToken, grant_type: 'refresh_token'}),
        url: window.apiUrls.refresh_token,
        headers: headers
      })

    LogIn: (username, password) ->
      $http({
        method: 'POST',
        data: $.param({username: username, password: password, grant_type: 'password'}),
        url: window.apiUrls.login,
        headers: headers
      })
        .then((data) ->
          return data.data
        )

    ExternalLogin: (provider, external_token) ->
      $http({
        method: 'POST',
        data: $.param({'external_system': provider, 'external_token': external_token}),
        url: window.apiUrls.login_register_external,
        headers: headers
      })
        .then((data) ->
          return data.data
        )

    Register: (user) ->
      $http({
        method: 'POST',
        data: $.param(user),
        url: apiUrl.register,
        headers: headers
      })
        .then((data) ->
          return data.data
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