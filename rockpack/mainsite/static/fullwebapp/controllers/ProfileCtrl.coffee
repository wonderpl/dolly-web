window.WebApp.controller('ProfileCtrl', ['$scope', 'UserManager', ($scope, UserManager) ->

  $scope.User = UserManager

  $scope.User.FetchSubscriptions()

])
