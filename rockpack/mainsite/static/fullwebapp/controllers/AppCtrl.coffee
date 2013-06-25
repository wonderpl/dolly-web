# TODO: Rejection reason is not captured

window.WebApp.controller('AppCtrl', ['$rootScope', '$location', 'UserManager', '$route', ($rootScope, $location, UserManager, $route) ->

  routesThatRequireAuth = ['/profile', '/feed']

  $rootScope.$on("$locationChangeStart", (event, NewUrl, OldUrl) ->

    if (UserManager.isLoggedIn == false)
      if (UserManager.credentials.refresh_token?)
        console.log 'in'
        event.preventDefault()
        UserManager.refreshToken()
          .success((data) ->
            UserManager.FetchUserData()
              .success((data) ->
                UserManager.FetchSubscriptions()
                  .success((data) ->
                    $route.reload()
                  )
              )
        )
      else
        if(_(routesThatRequireAuth).contains($location.path()))
          $location.path('/login')

  )
])
