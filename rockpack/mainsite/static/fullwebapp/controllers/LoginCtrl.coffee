window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'UserManager', '$rootScope', ($scope, $location, cookies, UserManager, $rootScope) ->

  $scope.User = UserManager

  #TODO: If user was redirected to login page, rediect him back to original page after login

  $scope.submit = ->
    if $scope.username? and $scope.password?
      $scope.User.LogIn($scope.username, $scope.password)
      .then((data) ->
          $scope.User.isLoggedIn = true
          $scope.User.FetchUserData(UserManager.credentials.resource_url)
            .then((data) ->
              $location.path('/feed')
            )
      )

  $scope.facebook = ->
    FB.login((response) ->
      if (response.authResponse)
        $scope.User.ExternalLogin('facebook', response.authResponse.accessToken)
        .success((data) ->
            $scope.User.isLoggedIn = true
            $scope.User.FetchUserData(UserManager.credentials.resource_url)
              .then((data) ->
                $location.path('/feed')
              )
          )
      else
        console.log 'canceled'
    )
  return
])