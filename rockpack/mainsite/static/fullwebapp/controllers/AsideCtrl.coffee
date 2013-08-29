window.WebApp.controller('AsideCtrl', ['$scope','UserManager', '$rootScope', 'playerService', ($scope, UserManager, $rootScope, playerService) ->

  $scope.$watch((()->playerService.getLocation()), (newValue) ->
    if newValue == 2
      $scope.channel = playerService.getChannel()
      $scope.video = playerService.getVideo()
      console.log $scope.channel
      console.log $scope.video
  )

  $scope.closeAside = () ->
    playerService.closePlayer()

  $scope.maximize = () ->
    playerService.setLocation(1)

  $scope.next = () ->
    playerService.playVideoFromChannel(playerService.getVideoPosition()+1)

  $scope.prev = () ->
    playerService.playVideoFromChannel(playerService.getVideoPosition()-1)
])