window.Weblight.controller('ChannelCtrl', ['$scope', 'Videos', '$routeParams', '$rootScope', '$location', 'isMobile', 'channelData', '$dialog', ($scope, Videos, $routeParams, $rootScope, $location, isMobile, channelData, $dialog) -> 

  @page = 1 # We prefetch the first page in the index (server side)
  @channelid = $routeParams.channelid
  
  $scope.isMobile = isMobile
  $scope.channel = channelData
  $rootScope.videos = channelData.videos.items

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
    # console.log 'video'
    $location.search( 'videoid', video.id );
    return

  $scope.$watch( ( -> $routeParams.videoid), (newVal, oldVal) ->
    if typeof newVal != 'undefined'

      videodata = {}
      # videodata = _.find($rootScope.videos, (video) -> 
      #   video.id == $routeParams.videoid
      # )

      d = $dialog.dialog({backdropFade: true, dialogFade: true, keyboard: true, backdropClick: true, dialogClass: 'playercontainer', resolve: videodata})
      d.open('videoplayer.html', 'VideoCtrl')
    return
  )

  $scope.getPlayerReady = -> 
    return $rootScope.playerReady

  return
])
