window.WebApp.controller('HeaderCtrl', ['$scope', 'cookies', 'OAuth', '$location', ($scope, cookies, OAuth, $location) ->

  $scope.logout = ->
    cookies.set('access_token', '')
    cookies.set('refresh_token', '')
    cookies.set('user_id', '')
    $location.path('/')

])
