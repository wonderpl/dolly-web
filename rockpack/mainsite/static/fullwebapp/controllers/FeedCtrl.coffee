window.WebApp.controller('FeedCtrl', ['$scope', 'cookies', 'userObj', ($scope, cookies, userObj) ->

  User = userObj

  $scope.feed = User.FetchRecentSubscriptions()

  console.log User
])
