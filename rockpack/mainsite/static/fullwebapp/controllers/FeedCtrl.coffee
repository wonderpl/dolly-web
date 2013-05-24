window.WebApp.controller('FeedCtrl', ['$scope', 'cookies', 'userObj', ($scope, cookies, userObj) ->

  $scope.User = userObj
  $scope.User.feed.position = 0

  $scope.load_feed = () ->
    $scope.User.FetchRecentSubscriptions($scope.User.feed.position, 10)
    $scope.User.feed.position += 10

  console.log 'aa'
#  $scope.load_feed()

  return
])
