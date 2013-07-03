# TODO: Handle direct links to video (video data has not been loaded yet)

window.WebApp.controller('VideoPlayerCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'ChannelData', ($scope, $rootScope, $routeParams, $location, ChannelData) ->

  $scope.channel = ChannelData

  $scope.PlayVideo = (videoid) =>
    if $rootScope.playerReady && $scope.channel.videos.items.length > 0

      $scope.videodata = _.find($scope.channel.videos.items, (video) ->
        video.id == videoid
      )

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

  $scope.$watch((-> $rootScope.playerReady), (newValue) ->
    if newValue
      $scope.PlayVideo($routeParams.video)
  )

  return
])
