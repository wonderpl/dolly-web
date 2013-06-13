window.WebApp.controller('ResetPasswordCtrl', ['$scope','$http', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, $location, cookies, OAuth, User) ->

  $scope.message = {}

  $scope.close = ->
    window.parent.postMessage('close', '*');

  $scope.resetPassword = ->
    $scope.error = ''
    OAuth.resetPassword($scope.username)
      .success((data) ->
        $scope.response = {message: "Check your email and follow the instructions", success: true}
      )
      .error((data)->
        $scope.response = {message: "Sorry we did not recognise this username or email", success: false}
      )

])