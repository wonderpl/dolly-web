window.WebApp.controller('HeaderCtrl', ['$scope', 'cookies', '$location', 'UserManager', ($scope, cookies, $location, UserManager) ->

  $scope.user = UserManager

  $scope.$watch('user.isLoggedIn', (newValue, oldValue) ->
    $scope.isLoggedIn = newValue
  )

  $scope.logout = ->
    $scope.user.logOut()
    $location.path("/login").replace()

])
