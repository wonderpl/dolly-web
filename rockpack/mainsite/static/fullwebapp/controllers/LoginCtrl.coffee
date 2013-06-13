window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'UserManager', '$rootScope', ($scope, $location, cookies, UserManager, $rootScope) ->

  $scope.User = UserManager

  #TODO: If user was redirected to login page, rediect him back to original page after login

  $scope.$on('$routeChangeSuccess', (event, currentRoute, previousRoute) ->
    console.log previousRoute
  )

  $scope.submit = ->
    if $scope.username? and $scope.password?
      $scope.User.Login($scope.username, $scope.password)
      .then((data) ->

        return
      )
    return

  return
])