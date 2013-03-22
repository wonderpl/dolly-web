window.Weblight.controller('ChannelCtrl', ['$scope', 'Videos', '$routeParams', '$rootScope', '$location', 'isMobile', 'channelData', ($scope, Videos, $routeParams, $rootScope, $location, isMobile, channelData) -> 

  @page = 1 # We prefetch the first page in the index (server side)
  @channelid = $routeParams.channelid
  
  @scope = isMobile
  $scope.channel = channelData
  $scope.channel.videos = channelData.videos

  $scope.load_videos = => 
    @page += 1
    Videos.get({start : @page*40, channelID: @channelid}, (data) ->
      $scope.videos.push.apply($scope.videos, data.videos.items)      
    )
    return

  $scope.setCurrentVideo = (video) ->
    $location.search( 'videoid', video.id );
    return

  return
])
