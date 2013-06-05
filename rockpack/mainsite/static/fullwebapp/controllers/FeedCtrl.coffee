window.WebApp.controller('FeedCtrl', ['$scope', 'cookies', 'userObj', ($scope, cookies, userObj) ->

  $scope.User = userObj
  $scope.User.feed.position = 0

  $scope.load_feed = () ->
    $scope.User.FetchRecentSubscriptions($scope.User.feed.position, 50)
    $scope.User.feed.position += 50

#  $scope.load_feed()

  return
])
