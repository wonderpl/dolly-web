window.WebApp.controller('RegisterCtrl', ['$scope', 'OAuth', 'locale', '$location', ($scope, OAuth, locale, $location) ->

  #TODO: Handle subscription fetching on registration

  $scope.register = (user) ->
    user.date_of_birth = "#{user.year}-#{user.month}-#{user.day}"
    user.locale = locale
    OAuth.register(user)
    .success((data) ->
        $location.path('/channels')
    )

])
