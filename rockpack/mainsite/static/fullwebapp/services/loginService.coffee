window.WebApp.factory('RefreshTokenService', ['UserManager', '$rootScope', 'OAuth', '$location', 'cookies', '$q', (UserManager, $rootScope, OAuth, $location, cookies, $q) ->

  deferred = $q.defer()
  refresh_token = cookies.get('refresh_token')
  user_id = cookies.get('user_id')

  User = UserManager

  # No user cradentials, redirect to login
  if (refresh_token == null or user_id == null)
    deferred.reject("error")
  else
    # Otherwise lets log in
    User.refreshToken(refresh_token)
    .success ((data) ->
      deferred.resolve(data)
    )

  return deferred.promise
])