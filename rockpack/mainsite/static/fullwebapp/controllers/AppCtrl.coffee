# TODO: Rejection reason is not captured

window.WebApp.controller('AppCtrl', ['$rootScope', '$location', 'UserManager', '$route', ($rootScope, $location, UserManager, $route) ->

  routesThatRequireAuth = ['/profile', '/feed']

  $rootScope.$on("$locationChangeStart", (event, NewUrl, OldUrl) ->

    if (UserManager.isLoggedIn == false)
      if (UserManager.oauth.credentials.refresh_token?)
        event.preventDefault()
        UserManager.oauth.refreshToken()
          .success((data) ->
            UserManager.isLoggedIn = true
            UserManager.FetchUserData()
              .then((data) ->
                $route.reload()
              )
        )
      else
        if(_(routesThatRequireAuth).contains($location.path()))
          $location.path('/login')

  )
])
