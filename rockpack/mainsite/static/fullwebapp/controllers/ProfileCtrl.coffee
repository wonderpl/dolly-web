window.WebApp.controller('ProfileCtrl', ['$scope', 'userObj', ($scope, userObj) ->

  $scope.User = userObj

  console.log $scope.User.details

])
