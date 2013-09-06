window.WebApp.controller('RegisterCtrl', ['$scope', 'UserManager', 'locale', '$location', ($scope, UserManager, locale, $location) ->

  $scope.register = (registrationForm) ->
    if registrationForm.$valid
      $scope.user.date_of_birth = "#{$scope.user.year}-#{$scope.user.month}-#{$scope.user.day}"
      $scope.user.locale = locale
      console.log $scope.user
      UserManager.Register($scope.user)
      .then((data) ->
          UserManager.FetchUserData(UserManager.resource_url)
            .then((data) ->
              $location.path('/channels')
            )
      )
    else
      console.log registrationForm


  $scope.facebook = ->
    FB.login((response) ->
      if (response.authResponse)
        UserManager.ExternalLogin('facebook', response.authResponse.accessToken)
      else
        console.log 'canceled'
    )

])
