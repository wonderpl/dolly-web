window.WebApp.controller('RegisterCtrl', ['$scope', 'UserManager', 'locale', '$location', ($scope, UserManager, locale, $location) ->

  #TODO: Handle subscription fetching on registration

  $scope.register = (user) ->
    user.date_of_birth = "#{user.year}-#{user.month}-#{user.day}"
    user.locale = locale
    UserManager.oauth.register(user)
    .success((data) ->
        $location.path('/channels')
    )

])
