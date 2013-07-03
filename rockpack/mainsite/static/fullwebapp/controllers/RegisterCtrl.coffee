window.WebApp.controller('RegisterCtrl', ['$scope', 'UserManager', 'locale', '$location', ($scope, UserManager, locale, $location) ->

  $scope.register = (user) ->
    user.date_of_birth = "#{user.year}-#{user.month}-#{user.day}"
    user.locale = locale
    UserManager.oauth.register(user)
    .success((data) ->
        console.log UserManager
        UserManager.isLoggedIn = true
        UserManager.FetchUserData(UserManager.oauth.credentials.resource_url)
          .then((data) ->
            $location.path('/channels')
          )
    )

])
