window.WebApp.controller('HeaderCtrl', ['$scope', 'cookies', 'OAuth', '$location', 'UserManager', ($scope, cookies, OAuth, $location, UserManager) ->

  $scope.user = UserManager

  $scope.logout = ->
    $scope.user.logOut()

])
