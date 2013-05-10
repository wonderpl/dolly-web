window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'OAuth', '$rootScope', ($scope, $location, cookies, OAuth, $rootScope) ->

  $scope.submit = ->
    if $scope.username? and $scope.password?
      OAuth.login($scope.username, $scope.password)
      .then((data) ->

        return
      )
    return

  return
])