window.WebApp.factory('RequireLoginService', ['UserManager', '$rootScope', '$location', '$q', (UserManager, $rootScope, $location, $q) ->


  return {
    checkLogin : () ->
      console.log 'check login'
      User = UserManager

      deferred = $q.defer()
      if User.credentials.refresh_token?
        console.log 'We have a refresh token (lets relog)'
        User.refreshToken(User.credentials.refresh_token)
          .success((data) ->
            console.log ("refresh token success")

            # Fetch full user details on first load (no previous refresh)
            User.FetchUserData(User.credentials.resource_url)
              .success((data) ->
                console.log 'success'
                deferred.resolve(User)
              )
          )
          .error((data) =>
            console.log ("Refresh fails, token might no longer be valid")
            console.log (data)
          )
      else
        console.log ("no user cradentials avilable, redirecting to login")
        $location.path("/login").replace()

      return deferred.promise
  }
])