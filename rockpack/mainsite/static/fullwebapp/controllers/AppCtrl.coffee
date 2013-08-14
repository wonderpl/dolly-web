# TODO: Location Change Start is not triggered is your in the site and navigate to a different page from the search bar
# For example, as an unregisteres user go to /login and then change url to /feed
# Possible Angularjs bug,

window.WebApp.controller('AppCtrl', ['$rootScope', '$location', 'UserManager', '$route', '$scope', ($rootScope, $location, UserManager, $route, $scope) ->

  routesThatRequireAuth = ['/feed']

  $rootScope.$on("$locationChangeStart", (event, NewUrl, OldUrl) ->

    if (UserManager.isLoggedIn == false)
      console.log 'user is logged off'
      if (UserManager.credentials.refresh_token?)
        event.preventDefault()
        UserManager.RefreshToken()
          .then((data) ->
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

  $scope.getWidth = () ->
    return $(window).width()



  $scope.$watch($scope.getWidth, (newValue, oldValue) ->
    if newValue > 1200
      $scope.sidebarWidth = 360
    else
      $scope.sidebarWidth = 246

    $rootScope.contentWidth = newValue - $scope.sidebarWidth + 'px'

  )

  window.onresize = () ->
    $scope.$apply()

])
