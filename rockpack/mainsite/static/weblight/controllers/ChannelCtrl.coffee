window.Weblight.controller('ChannelCtrl', ['$scope', 'Videos', '$routeParams', '$rootScope', '$location', 'isMobile', 'channelData', ($scope, Videos, $routeParams, $rootScope, $location, isMobile, channelData) -> 

  @page = 1 # We prefetch the first page in the index (server side)
  @channelid = channelData.id

  $scope.isMobile = isMobile
  $scope.channel = channelData
  $scope.videos = channelData.videos.items

  #http://media.dev.rockpack.com/images/channel/thumbnail_medium/prWVvv-dUZfY33SmzrecPg.jpg

  $scope.channel.thumbnail = channelData.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_small')
  $scope.channel.owner.avatar = channelData.owner.avatar_thumbnail_url.replace('thumbnail_small', 'thumbnail_large')


  $scope.$watch('isVertical', (newValue, oldValue) ->
    if $scope.isVertical
      $scope.channel.cover = channelData.cover.thumbnail_url.replace('thumbnail_medium', 'background_portrait')
    else
      $scope.channel.cover = channelData.cover.thumbnail_url.replace('thumbnail_medium', 'background')
  )

  # Additional defaults
  $scope.videoCellTitleLength = if $scope.isMobile then 20 else 25
  $scope.channelTitleLength = if $scope.isMobile then 15 else 25

  @totalvideos = channelData.videos.total

  $scope.load_videos = => 

    #only try to fech videos if there are hidden videos in the channel
    if @page*40 <= @totalvideos
      Videos.get(@channelid, 40, @page*40, '').then (data) =>
        _.each(data, (video) =>
          $scope.videos.push(video)
        )
      @page += 1
    return

  $scope.setCurrentVideo = (video) ->
    $location.search( 'videoid', video.id );
    return

  return
])
