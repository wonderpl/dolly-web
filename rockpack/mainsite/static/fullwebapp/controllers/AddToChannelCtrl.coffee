window.WebApp.controller('AddtoChannelCtrl', ['$scope','UserManager', 'videoId', 'dialog', ($scope, UserManager, videoId, dialog) ->

  $scope.channels = UserManager.details.channels.items
  console.log UserManager.details.channels.items
  $scope.videoID = videoId
  $scope.selectedChannel = null

  $scope.selectChannel = (channelurl) ->
    $scope.selectedChannel  = channelurl
    return

  $scope.close = () ->
    dialog.close()

  $scope.addtoChannel = () ->
    if $scope.selectedChannel != null
      UserManager.addVideo($scope.selectedChannel,$scope.videoID)
        .success((data) ->
          dialog.close()
        )
        .error((data) ->
          alert data
        )
])