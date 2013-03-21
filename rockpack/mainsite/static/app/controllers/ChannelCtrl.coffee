window.Weblight.controller('ChannelCtrl', ['$scope', 'Videos', '$routeParams', '$rootScope', '$location', 'isMobile', ($scope, Videos, $routeParams, $rootScope, $location, isMobile) -> 
  @page = 0
  @channelid = $routeParams.channelid
  
  @scope = isMobile
  $scope.channel = Videos.get({start: @page, channelID: @channelid}, (data) ->
    $scope.videos = $scope.channel.videos.items
    return
  )
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
