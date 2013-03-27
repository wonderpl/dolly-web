window.Weblight.controller('ChannelCtrl', ['$scope', 'Videos', '$routeParams', '$rootScope', '$location', 'isMobile', 'channelData', ($scope, Videos, $routeParams, $rootScope, $location, isMobile, channelData) -> 

  @page = 1 # We prefetch the first page in the index (server side)
  @channelid = $routeParams.channelid
  
  $scope.isMobile = isMobile
  $scope.channel = channelData
  $scope.videos = channelData.videos.items

  # Additional defaults
  $scope.videoCellTitleLength = if $scope.isMobile then 20 else 25
  $scope.channelTitleLength = if $scope.isMobile then 15 else 25

  @totalvideos = channelData.videos.total

  $scope.load_videos = => 

    #only try to fech videos if there are hidden videos in the channel
    if @page*40 <= @totalvideos
      Videos.get({start : @page*40, channelID: @channelid}, (data) =>
        $scope.videos.push.apply($scope.videos, data.videos.items)      
        @page += 1
      )
    return

  $scope.setCurrentVideo = (video) ->
    $location.search( 'videoid', video.id );
    return

  return
])
