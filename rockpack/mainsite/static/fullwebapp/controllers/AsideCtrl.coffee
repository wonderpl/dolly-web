window.WebApp.controller('AsideCtrl', ['$scope','UserManager', '$rootScope', ($scope, UserManager, $rootScope) ->

  $scope.closeAside = () ->
    $rootScope.asideOpen = false
])