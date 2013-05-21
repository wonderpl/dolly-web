angular.module('Bookmarklet').factory('OAuth', ($http, api_urls, $q) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  # TOOD: Implement Facebook registration/login
  oauth_urls = api_urls

  OAuth = {

    login: (username, password) ->
      deferred = $q.defer()
      $http({
        method: 'POST',
        data: $.param({username: username, password: password, grant_type: 'password'}),
        url: oauth_urls.login,
        headers: headers
      }).success((data) ->
        deferred.resolve(data)
      ).error((data)->
        deferred.reject()
      )
      return deferred.promise

    refreshToken: (refreshToken) ->
      deferred = $q.defer()
      $http({
        method: 'POST',
        data: $.param({refresh_token: refreshToken, grant_type: 'refresh_token'}),
        url: oauth_urls.refresh_token,
        headers: headers
      }).success((data) ->
        deferred.resolve(data)
      ).error((data)->
        deferred.reject()
      )
      return deferred.promise

    # Accepts Username or Email (supplied as username)
    resetPassword: (username) ->
      deferred = $q.defer()
      $http({
        method: 'POST',
        data: $.param({username: username}),
        url: oauth_urls.reset_password,
        headers: headers
      }).success((data) ->
        deferred.resolve(data)
      ).error((data)->
        deferred.reject()
      )

    externalLogin: (provider, external_token) ->
      deferred = $q.defer()
      $http({
        method: 'POST',
        data: $.param({'external_system': provider, 'external_token': external_token}),
        url: oauth_urls.login_register_external,
        headers: headers
      }).success((data) ->
        deferred.resolve(data)
      ).error((data)->
        deferred.reject()
      )
  }

  return OAuth
)