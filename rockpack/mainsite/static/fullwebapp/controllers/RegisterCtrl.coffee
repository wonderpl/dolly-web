window.WebApp.controller('RegisterCtrl', ['$scope', 'UserManager', 'locale', '$location', ($scope, UserManager, locale, $location) ->

  $scope.user = {}

  $scope.register = (user) ->
    console.log user
    user.date_of_birth = "#{user.year}-#{user.month}-#{user.day}"
    user.locale = locale
    UserManager.Register(user)
    .then((data) ->
        UserManager.FetchUserData(UserManager.resource_url)
          .then((data) ->
            $location.path('/channels')
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
                $location.path('/channels')
              )
          )
      else
        console.log 'canceled'
    )

])
