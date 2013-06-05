window.Weblight.controller('ChannelCtrl', ['$scope', 'Videos', '$routeParams', '$rootScope', '$location', 'isMobile', 'channelData', ($scope, Videos, $routeParams, $rootScope, $location, isMobile, channelData) ->

  @page = 1 # We prefetch the first page in the index (server side)
  @channelid = channelData.id

  $scope.isMobile = isMobile
  $scope.channel = channelData
  $scope.videos = channelData.videos.items


  $scope.channel.owner.avatar = channelData.owner.avatar_thumbnail_url.replace('thumbnail_small', 'thumbnail_large')
  $scope.coverRegex = new RegExp("channel/.*/")


  $scope.$watch('isVertical', (newValue, oldValue) ->
    if $scope.isVertical
      $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background_portrait/')
    else
      $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background/')
  )


  # Additional defaults
  $scope.videoCellTitleLength = if $scope.isMobile then 40 else 50
  $scope.channelTitleLength = if $scope.isMobile then 15 else 25

  @totalvideos = channelData.videos.total

  $scope.load_videos = => 

    #only try to fech videos if there are hidden videos in the channel
    if @page*40 <= @totalvideos
      Videos.get(40, @page*40).then (data) =>
        _.each(data, (video) =>
          $scope.videos.push(video)
        )
      @page += 1
    return

  $scope.setCurrentVideo = (video) ->
    ga('send', 'event', 'uiAction', 'videoPlayClick')
    $location.search( 'video', video.id );
    return

  # Catch share of specific video url
  url = $location.absUrl()
  if url.indexOf('?video=') > 0 and not $routeParams.video?
    $location.search( 'video',url.substring(url.indexOf('?video=')+7, url.length-2))


  return
])
