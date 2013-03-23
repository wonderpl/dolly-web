window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', ($scope, $rootScope, $routeParams, $location) ->

  $rootScope.currentVideo = {}

  $scope.options = {
    backdropFade: true,
    dialogFade: true,
    keyboard: true,
    backdropClick: true
  }


  $scope.getPlayerReady = -> 
    return $rootScope.playerReady

  $scope.getVideoId = ->
    return $routeParams.videoid

  $scope.PlayVideo = ->
    if $rootScope.playerReady && typeof $routeParams.videoid != "undefined"
      $scope.shouldBeOpen = true
      $scope.videodata = _.find($scope.videos, (video) -> 
        video.id == $routeParams.videoid
      )
      # if typeof $scope.player != "undefined" 
      #   $scope.player.loadVideoById($scope.videodata.video.source_id, 0, 'highres')
      # else 
      $scope.player = new YT.Player('player', {
        height: '415',
        width: '738',
        videoId: $scope.videodata.video.source_id,
        playerVars: {
          autoplay: 1,
          showinfo: 0,
          modestbranding: 0
        }
      })

  $scope.$watch($scope.getVideoId, (newValue) ->
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.$watch($scope.getPlayerReady, (newValue) ->
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.close = ->
    console.log 'close'
    # $scope.player.stopVideo()
    $scope.shouldBeOpen = false
    $location.search( 'videoid', null )
    return

  return
])
