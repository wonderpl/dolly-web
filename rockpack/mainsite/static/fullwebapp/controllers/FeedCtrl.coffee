window.WebApp.controller('FeedCtrl', ['$scope', 'cookies', 'UserManager', ($scope, cookies, UserManager) ->

  $scope.User = UserManager

  $scope.load_feed = () ->
    if ($scope.User.feed.total == null or $scope.User.feed.total > $scope.User.feed.position)
      $scope.User.FetchRecentSubscriptions($scope.User.feed.position, 50)
      $scope.User.feed.position += 50

  return
])
