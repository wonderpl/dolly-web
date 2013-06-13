window.WebApp.controller('HeaderCtrl', ['$scope', 'cookies', 'OAuth', '$location', 'UserManager', ($scope, cookies, OAuth, $location, UserManager) ->

  $scope.user = UserManager

  $scope.$watch('user.loggedIn', (newValue, oldValue) ->
    $scope.LoggedIn = newValue
  )

  $scope.logout = ->
    $scope.user.logOut()
    $location.path("/login").replace()

])
