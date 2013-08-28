# TODO: Location Change Start is not triggered is your in the site and navigate to a different page from the search bar
# For example, as an unregisteres user go to /login and then change url to /feed
# Possible Angularjs bug,

window.WebApp.controller('AppCtrl', ['$rootScope', '$location', 'UserManager', '$route', '$scope', 'playerService', ($rootScope, $location, UserManager, $route, $scope, playerService) ->

  $rootScope.asideOpen = false

  routesThatRequireAuth = ['/channels']

  $rootScope.$on("$locationChangeStart", (event, NewUrl, OldUrl) ->

    if (UserManager.isLoggedIn == false)
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

  #TODO The browser does not trigger a width change when the scroll bar is added, will cause some problem in edge cases and needs to be fixed

  $scope.$watch($scope.getWidth, (newValue, oldValue) ->
    ContentWidthCalculator()
  )

  $scope.$watch('asideOpen', (newValue, oldValue) ->
    ContentWidthCalculator()
  )

  ContentWidthCalculator = () ->
    width = $scope.getWidth()
    if width > 1200
      $scope.sidebarWidth = 360
    else
      $scope.sidebarWidth = 246

    if $rootScope.asideOpen
      $rootScope.contentWidth = width - $scope.sidebarWidth + 'px'
    else
      $rootScope.contentWidth = '100%'

  window.onresize = () ->
    $scope.$apply()

  # Expose the assets
  $rootScope.assets_url = window.assets_url

  #
  $scope.showFullPlayer = false

  $scope.$watch((()-> playerService.getVideo()), (newValue) ->
    if newValue?
      $scope.showFullPlayer = true
  )

  $scope.$watch((()-> playerService.getLocation()), (newValue) ->
    if newValue == 2
      $rootScope.asideOpen = true
    else
      $rootScope.asideOpen = false
  )

])
