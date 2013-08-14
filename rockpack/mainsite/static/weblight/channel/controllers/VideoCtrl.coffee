window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'isMobile', 'userService', ($scope, $rootScope, $routeParams, $location, isMobile, userService) ->

  $scope.triggerEvent = (action, label) ->
    ga('send', 'event', 'uiAction', action, label)

  $scope.videoVisible = false

  windowWidth = if "innerWidth" in window then window.innerWidth else document.documentElement.offsetWidth

  @getPlayerWidth = () ->
    if windowWidth <= 979
      @playerWidth = 300
      @playerHeight = 169
    else
      @playerWidth = 620
      @playerHeight = 349

  $scope.PlayVideo = =>
    if $rootScope.playerReady && typeof $routeParams.video != "undefined"

      @getPlayerWidth()


      $scope.videoVisible = true
      $scope.player = new YT.Player('player', {
        height: @playerHeight,
        width: @playerWidth,
        videoId: $scope.videodata.video.source_id,
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
          'onReady': onPlayerReady,
          'onStateChange': onPlayerStateChange
        }

      })

  $scope.isSkeeping = false

  $scope.seekTo = (event) ->
    isSkeeping = true
    seekPosition = event.offsetX / 620
    $scope.player.seekTo($scope.player.getDuration() * seekPosition )
    $scope.player.playVideo()
    $scope.playerState = 1

  onPlayerReady = (event) ->
    $scope.player.mute()

  onPlayerStateChange = (event) ->
    $scope.playerState = event.data
    $scope.$apply()

    if event.data == 1
      setTimeout(trackProgress, 40)

  $scope.currentPosition = 0

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


  $scope.closeVideo = () ->
    $scope.player.destroy()
    $location.search('video', null)
    $scope.videoVisible = false



  $scope.playNextVid = (videoNumber) ->
    if videoNumber < -5 or  videoNumber > $scope.videos.length-1
      $scope.videoNum = 0
    else
      if videoNumber < 0
        $scope.videoNum = $scope.videos.length-1
      else
        $scope.videoNum = videoNumber

    $location.search( 'video',$scope.videos[$scope.videoNum].id)

  $scope.$watch((-> $routeParams.video), (newValue) ->
    if newValue?
      $scope.PlayVideo()
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

  return
])
