window.WebApp.controller('ProfileCtrl', ['$scope', 'UserManager', '$routeParams', ($scope, UserManager, $routeParams) ->

  $scope.User = UserManager
  if $scope.User.isLoggedIn and $routeParams.userid == $scope.User.details.user_id
    $scope.User.FetchNotifications()
    $scope.User.FetchSubscriptions()
  else
    # Fetch external user data

])
