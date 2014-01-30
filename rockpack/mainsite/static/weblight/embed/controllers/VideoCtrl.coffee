window.WebLite.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', ($scope, $rootScope, $routeParams, $location) ->

  $rootScope.videoPosition = null
  $scope.currentPosition = 0

  @getPlayerWidth = () ->
    @playerWidth = 430
    @playerHeight = 242

  $scope.PlayVideo = =>
    if $rootScope.playerReady && $scope.currVideo?

      @getPlayerWidth()

      if $scope.player?
        $scope.player.loadVideoById($scope.currVideo)
      else
        $scope.player = new YT.Player('player', {
          height: @playerHeight,
          width: @playerWidth,
          videoId: $scope.currVideo,
          playerVars: {
            autoplay: 1,
            showinfo: 0,
            modestbranding: 1,
            wmode: "opaque",
            controls: 0,
            color: 'white',
            rel: 0,
            iv_load_policy: 3,
          },
          events: {
            'onStateChange': onPlayerStateChange
          }

        })
    $scope.isSkeeping = false

  $scope.seekTo = (event) ->
    isSkeeping = true
    seekPosition = event.offsetX / 430
    $scope.player.seekTo($scope.player.getDuration() * seekPosition )
    $scope.player.playVideo()
    $scope.playerState = 1

  onPlayerStateChange = (event) ->
    $scope.playerState = event.data
    $scope.$apply()

    if event.data == 1
      setTimeout(trackProgress, 40)
    else if event.data == 0
      if $rootScope.videoPosition < window.channel_data.videos.total
        $rootScope.videoPosition++
        $rootScope.$apply()

  $scope.next = () ->
    if $rootScope.videoPosition < window.channel_data.videos.total
      $rootScope.videoPosition++


  $scope.prev = () ->
    if $rootScope.videoPosition > 0
      $rootScope.videoPosition--

  trackProgress = () ->
    if $scope.playerState == 1
      $scope.currentPosition = $scope.player.getCurrentTime()/$scope.player.getDuration()
      $scope.$apply()
      setTimeout(trackProgress, 40)


  $scope.hideOverlay = false

  setTimeout((->
    $scope.hideOverlay = true
  ), 100)

  $scope.mouseOver = () ->
    $scope.hideOverlay = false

  $scope.mouseOut = () ->
    $scope.hideOverlay = true


  $scope.$watch((-> $rootScope.videoPosition), (newValue) ->
    if newValue?
      $scope.currVideo = window.channel_data.videos.items[newValue].video.source_id
      $scope.PlayVideo()
    else
      if $scope.player? 
        $scope.player.stopVideo()
    return
  )


  $scope.$watch((-> $rootScope.playerReady), (newValue) ->
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.pausePlay = () ->
    if $scope.player.getPlayerState() == 1
      $scope.player.pauseVideo()
    else if $scope.player.getPlayerState() == 2
      $scope.player.playVideo()

  $scope.getVideoPosition = (videoId) ->
    _.find(window.channel_data.videos.items, (video) ->
      return video.video.source_id == videoId
    )

  $scope.close = () ->
    $scope.currVideo = null
    $rootScope.videoPosition = null

  return
])
