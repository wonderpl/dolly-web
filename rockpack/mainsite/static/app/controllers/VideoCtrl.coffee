window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', ($scope, $rootScope, $routeParams, $location) ->
  
  $rootScope.currentVideo = {}

  $scope.getVideoId = ->
    return $routeParams.videoid

  $scope.PlayVideo = ->
    if $rootScope.playerReady && typeof $routeParams.videoid != "undefined"
      $("#lightbox").hide()
      $("#lightbox").show()
      $scope.videodata = _.find($scope.videos, (video) -> 
        video.id == $routeParams.videoid
      )
      if typeof $scope.player != "undefined" 
        $scope.player.loadVideoById($scope.videodata.video.source_id, 0, 'highres')
      else 
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

  $scope.$watch((-> $rootScope.playerReady), (newValue) ->
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.hide = ->
    $scope.player.stopVideo()
    $('#lightbox').hide()
    $location.search( 'videoid', null );
    return

  return
])
