window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'UserManager', '$rootScope', ($scope, $location, cookies, UserManager, $rootScope) ->

  $scope.User = UserManager

  #TODO: If user was redirected to login page, rediect him back to original page after login

  console.log 'Login Control'

  $scope.$on('$routeChangeSuccess', (event, currentRoute, previousRoute) ->
    console.log previousRoute
  )

  $scope.submit = ->
    if $scope.username? and $scope.password?
      $scope.User.oauth.Login($scope.username, $scope.password)
      .success((data) ->
          $scope.User.isLoggedIn = true
          $scope.User.FetchUserData(UserManager.oauth.credentials.resource_url)
            .success((data) ->
              $location.path('/feed')
            )
      )

  $scope.facebook = ->
    FB.login((response) ->
      if (response.authResponse)
        $scope.User.ExternalLogin('facebook', response.authResponse.accessToken)
        .success((data) ->
            $scope.User.isLoggedIn = true
          )
      else
        console.log 'canceled'
    )
  return
])