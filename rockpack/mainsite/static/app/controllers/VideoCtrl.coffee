window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', ($scope, $rootScope, $routeParams, $location) ->
  
  $rootScope.currentVideo = {}


  $scope.getPlayerReady = ->
    return $rootScope.playerReady

  $scope.getVideoId = ->
    return $routeParams.videoid

  $scope.PlayVideo = ->
    if $scope.getPlayerReady() && typeof $routeParams.videoid != "undefined"
      $scope.videodata = _.find($scope.videos, (video) -> 
        video.id == $routeParams.videoid
      )
      if typeof $scope.player == "undefined"
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
      else 
        $scope.player.loadVideoById($scope.videodata.video.source_id, 0, 'highres')
      $("#lightbox").show()      

  $scope.$watch($scope.getVideoId, (newValue) ->
    $scope.PlayVideo()
    return
  )

  $scope.$watch($scope.getPlayerReady, (newValue) ->
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
