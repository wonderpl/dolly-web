window.WebApp.factory('RequireLoginService', ['UserManager', '$rootScope', '$location', '$q', (UserManager, $rootScope, $location, $q) ->


  return {
    checkLogin : () ->
      User = UserManager

      deferred = $q.defer()
      if User.loggedIn
        console.log 'User already logged in'
        deferred.resolve(User)
      else
        console.log ("no user cradentials avilable, redirecting to login")
        $location.path("/login").replace()

      return deferred.promise
  }
])