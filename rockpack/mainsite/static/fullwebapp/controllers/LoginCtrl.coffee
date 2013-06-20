window.WebApp.controller('LoginCtrl', ['$scope', '$location', 'cookies', 'UserManager', '$rootScope', ($scope, $location, cookies, UserManager, $rootScope) ->

  $scope.User = UserManager

  #TODO: If user was redirected to login page, rediect him back to original page after login

  $scope.$on('$routeChangeSuccess', (event, currentRoute, previousRoute) ->
    console.log previousRoute
  )

  $scope.submit = ->
    if $scope.username? and $scope.password?
      $scope.User.Login($scope.username, $scope.password)
      .success((data) ->
          UserManager.FetchUserData(UserManager.credentials.resource_url)
            .success((data) ->
              $location.path('/feed')
            )
      )

  $scope.facebook = ->
    FB.login((response) ->
      if (response.authResponse)
        # connected
        $scope.User.ExternalLogin('facebook', response.authResponse.accessToken)
      else
        console.log 'canceled'
    )
  return
])