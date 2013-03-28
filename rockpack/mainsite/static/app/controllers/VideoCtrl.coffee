window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'isMobile', ($scope, $rootScope, $routeParams, $location, isMobile) ->


  $rootScope.currentVideo = {}

  @getPlayerWidth = ->
    console.log window.innerWidth
    if window.innerWidth < 750
      @playerWidth = window.innerWidth
      @playerHeight = window.innerWidth*9/16
    else
      @playerWidth = 738
      @playerHeight = 415


  $scope.PlayVideo = =>
    if $rootScope.playerReady && typeof $routeParams.videoid != "undefined"

      @getPlayerWidth()

      # need to trigger a hide, otherwise show did not fire on load
      $("#lightbox").hide()
      $("#lightbox").show()
      $scope.videodata = _.find($scope.videos, (video) -> 
        video.id == $routeParams.videoid
      )
      # if typeof $scope.player != "undefined" 
      #   $scope.player.loadVideoById($scope.videodata.video.source_id, 0, 'highres')
      # else 
      console.log @playerWidth
      $scope.player = new YT.Player('player', {
        height: @playerHeight,
        width: @playerWidth,
        videoId: $scope.videodata.video.source_id,
        playerVars: {
          autoplay: 1,
          showinfo: 0,
          modestbranding: 0,
          wmode: "opaque"
        }
      })

  $scope.$watch((-> window.orientation), (newValue, oldValue) =>
    if oldValue != newValue
      @getPlayerWidth()
      $('#player').width(@playerWidth).height(@playerHeight)

  )

  $scope.$watch((-> $routeParams.videoid), (newValue) ->
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
    $location.search( 'videoid', null );
    return

  return
])
