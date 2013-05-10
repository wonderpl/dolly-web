window.WebApp.controller('FeedCtrl', ['$scope', 'cookies', 'userObj', ($scope, cookies, userObj) ->

  User = userObj

  console.log User.details
])
