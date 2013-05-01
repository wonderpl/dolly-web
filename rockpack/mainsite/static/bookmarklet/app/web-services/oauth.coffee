angular.module('Bookmarklet').factory('OAuth', ($http, apiUrl, $q) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  # TOOD: Implement Facebook registration/login

  OAuth = {

    login: (username, password) ->
      deferred = $q.defer()
      $http({
        method: 'POST',
        data: $.param({username: username, password: password, grant_type: 'password'}),
        url: apiUrl + 'ws/login/',
        headers: headers
      }).success((data) ->
        deferred.resolve(data)
      ).error((data)->
        deferred.reject()
      )
      return deferred.promise

    register: (userParms) ->
      deferred = $q.defer()
      $http({
        method: 'POST',
        data: $.param(userParms),
        url: apiUrl + 'ws/register/',
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
        url: apiUrl + 'ws/token/',
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
        data: $.param({username: username, grant_type: 'refresh_token'}),
        url: apiUrl + 'ws/reset-password/',
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
        url: apiUrl + 'ws/login/external/',
        headers: headers
      }).success((data) ->
        deferred.resolve(data)
      ).error((data)->
        deferred.reject()
      )
  }

  return OAuth
)