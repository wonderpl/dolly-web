window.WebApp.controller('RegisterCtrl', ['$scope', 'UserManager', ($scope, UserManager) ->

  console.log 'aaa'
  $scope.User = UserManager

  $scope.register = (user) ->
    console.log user

])
