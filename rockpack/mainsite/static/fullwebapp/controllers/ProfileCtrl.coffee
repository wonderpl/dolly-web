window.WebApp.controller('ProfileCtrl', ['$scope', 'UserManager', '$routeParams', 'subscriptionsService', 'loggedoutUserService', ($scope, UserManager, $routeParams, subscriptionsService, loggedoutUserService) ->

  if UserManager.isLoggedIn and $routeParams.userid == UserManager.credentials.user_id
    $scope.channels = UserManager.details.channels.items
    $scope.User = UserManager
    UserManager.FetchSubscriptions()
      .success((data) ->
        $scope.subscriptions = UserManager.details.subscriptions.subscribedChannels.items
      )
  else
    $scope.subscriptions = subscriptionsService.FetchSubscriptions($routeParams.userid)
    $scope.User = {
      credentials: {
        user_id: $routeParams.userid
      }
      details: loggedoutUserService.fetchUser($routeParams.userid)
    }
])
