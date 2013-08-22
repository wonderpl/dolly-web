window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'UserManager', '$rootScope', ($scope, $location, cookies, UserManager, $rootScope) ->

  $scope.User = UserManager

  $scope.submit = ->
    if $scope.username? and $scope.password?
      $scope.User.LogIn($scope.username, $scope.password)
      .then((data) ->
          $scope.User.isLoggedIn = true
          $scope.User.FetchUserData(UserManager.credentials.resource_url)
            .then((data) ->
              $location.path('/channels')
            )
      )

  $scope.facebook = ->
    FB.login((response) ->
      if (response.authResponse)
        $scope.User.ExternalLogin('facebook', response.authResponse.accessToken)
      else
        console.log 'canceled'
    )
  return
])