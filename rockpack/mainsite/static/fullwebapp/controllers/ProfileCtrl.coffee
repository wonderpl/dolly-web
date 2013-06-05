window.WebApp.controller('ProfileCtrl', ['$scope', 'userObj', ($scope, userObj) ->

  $scope.User = userObj

  $scope.User.FetchSubscriptions()

])
