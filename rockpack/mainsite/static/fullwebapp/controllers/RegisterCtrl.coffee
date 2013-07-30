window.WebApp.controller('RegisterCtrl', ['$scope', 'UserManager', 'locale', '$location', ($scope, UserManager, locale, $location) ->

  $scope.register = (user) ->
    user.date_of_birth = "#{user.year}-#{user.month}-#{user.day}"
    user.locale = locale
    UserManager.Register(user)
    .then((data) ->
        UserManager.FetchUserData(UserManager.resource_url)
          .then((data) ->
            $location.path('/channels')
          )
    )

])
