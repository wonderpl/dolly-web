window.WebApp.controller('ResetPasswordCtrl', ['$scope','$http', '$location', 'cookies', 'UserManager', 'User', ($scope, $http, $location, cookies, UserManager, User) ->

  $scope.message = {}

  $scope.close = ->
    window.parent.postMessage('close', '*');

  $scope.resetPassword = ->
    $scope.error = ''
    UserManager.resetPassword($scope.username)
      .success((data) ->
        $scope.response = {message: "Check your email and follow the instructions", success: true}
      )
      .error((data)->
        $scope.response = {message: "Sorry we did not recognise this username or email", success: false}
      )

])