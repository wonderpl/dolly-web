window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'OAuth', '$rootScope', ($scope, $location, cookies, OAuth, $rootScope) ->

  if User?
    $location.path('/feed')

  $scope.submit = ->
    if $scope.username? and $scope.password?
      OAuth.login($scope.username, $scope.password)
      .then((data) ->
        $rootScope.User = data
        return
      )
    return

  return
])