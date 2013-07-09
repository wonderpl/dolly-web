window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'isMobile', ($scope, $rootScope, $routeParams, $location, isMobile) ->

  $scope.triggerEvent = (action, label) ->
    ga('send', 'event', 'uiAction', action, label)

  @getPlayerWidth = () ->
    if $(window).width() <= 979
      @playerWidth = 320
      @playerHeight = 240
    else
      @playerWidth = 840
      @playerHeight = 473

  console.log $(window).width()
  console.log @playerWidth

  $scope.videoNum = -10

  $scope.PlayVideo = =>
    if $rootScope.playerReady && typeof $routeParams.video != "undefined"

      @getPlayerWidth()

      # need to trigger a hide, otherwise show did not fire on load
      $("#lightbox").hide()
      $("#lightbox").show()

      $scope.videodata = window.selected_video

      $scope.player = new YT.Player('player', {
        height: @playerHeight,
        width: @playerWidth,
        videoId: $scope.videodata.video.source_id,
        playerVars: {
          autoplay: 1,
          showinfo: 0,
          modestbranding: 1,
          wmode: "opaque",
          controls: 1,
          color: 'white',
          rel: 0,
          iv_load_policy: 3
        }
      })

  onPlayerReady = (event) ->
    event.target.playVideo()

  $scope.$watch((-> window.orientation), (newValue, oldValue) =>
    if oldValue != newValue
      @getPlayerWidth()
      $('#player').width(@playerWidth).height(@playerHeight)

  )

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
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.$watch((-> $rootScope.playerReady), (newValue) ->
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.hide = ->
    $('#lightbox').hide()
    $scope.player.destroy()
    $scope.player = null
    $location.search( 'video', null );
    return

  return
])
