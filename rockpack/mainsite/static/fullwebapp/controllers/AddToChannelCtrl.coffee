window.WebApp.controller('AddtoChannelCtrl', ['$scope','UserManager', 'videoId', '$dialog', ($scope, UserManager, videoId, $dialog) ->

  console.log videoId
  $scope.channels = UserManager.details.channels.items
  $scope.videoID = videoId
  $scope.selectedChannel = null

  console.log UserManager

  $scope.selectChannel = (channelurl) ->
    $scope.selectedChannel  = channelurl
    return

  $scope.addtoChannel = () ->
    if $scope.selectedChannel != null
      UserManager.addVideo($scope.selectedChannel,$scope.videoID)
        .success((data) ->
          $dialog.close
        )
        .error((data) ->
          alert data
        )
])