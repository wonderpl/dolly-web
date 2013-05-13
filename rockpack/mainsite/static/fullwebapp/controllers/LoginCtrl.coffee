window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'UserManager', '$rootScope', ($scope, $location, cookies, UserManager, $rootScope) ->

  $scope.User = UserManager


  console.log $scope.User
  $scope.submit = ->
    if $scope.username? and $scope.password?
      $scope.User.Login($scope.username, $scope.password)
      .then((data) ->

        return
      )
    return

  return
])