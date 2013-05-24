window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'isMobile', ($scope, $rootScope, $routeParams, $location, isMobile) ->


  $rootScope.currentVideo = {}

  @getPlayerWidth = ->
    if window.window.screen.width < 750
      @playerWidth = window.window.screen.width
      @playerHeight = window.window.screen.width*9/16
    else
      @playerWidth = 840
      @playerHeight = 473


  $scope.PlayVideo = =>
    if $rootScope.playerReady && typeof $routeParams.video != "undefined"

      @getPlayerWidth()

      # need to trigger a hide, otherwise show did not fire on load
      $("#lightbox").hide()
      $("#lightbox").show()
      $scope.videodata = _.find($scope.videos, (video) -> 
        video.id == $routeParams.video
      )
      # if typeof $scope.player != "undefined" 
      #   $scope.player.loadVideoById($scope.videodata.video.source_id, 0, 'highres')
      # else 
      $scope.player = new YT.Player('player', {
        height: @playerHeight,
        width: @playerWidth,
        videoId: $scope.videodata.video.source_id,
        playerVars: {
          autoplay: 1,
          showinfo: 1,
          modestbranding: 1,
          wmode: "opaque",
          controls: 1
        }
      })

  onPlayerReady = (event) ->
    event.target.playVideo()

  $scope.$watch((-> window.orientation), (newValue, oldValue) =>
    if oldValue != newValue
      @getPlayerWidth()
      $('#player').width(@playerWidth).height(@playerHeight)

  )

  $scope.$watch((-> $routeParams.video), (newValue) ->
    console.log 'got player id'
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
    $location.search( 'video', null );
    return

  return
])
