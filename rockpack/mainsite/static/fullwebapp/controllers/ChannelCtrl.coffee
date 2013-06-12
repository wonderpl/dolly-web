window.WebApp.controller('ChannelCtrl', ['$scope', '$routeParams', '$rootScope', '$location', ($scope, $routeParams, $rootScope, $location) ->

  @page = 0

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

  if selected_video != null
    $location.search( 'video',selected_video.id)

  return
])
