# TODO: Location Change Start is not triggered is your in the site and navigate to a different page from the search bar
# For example, as an unregisteres user go to /login and then change url to /feed
# Possible Angularjs bug,

window.WebApp.controller('AppCtrl', ['$rootScope', '$location', 'UserManager', '$route', ($rootScope, $location, UserManager, $route) ->

  routesThatRequireAuth = ['/profile', '/feed']

  $rootScope.$on("$locationChangeStart", (event, NewUrl, OldUrl) ->

    console.log 'testing transition'
    if (UserManager.oauth.isLoggedIn == false)
      console.log 'user is logged off'
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
          $rootScope.message = {
            message: 'Please register before you proceed'
            state: 0
          }
          $location.path("/login")

  )
])
