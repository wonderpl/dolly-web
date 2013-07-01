window.WebApp.controller('VideoPlayerCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'ChannelData', ($scope, $rootScope, $routeParams, $location, ChannelData) ->

  $scope.channel = ChannelData

  console.log $scope.channel

  $scope.PlayVideo = =>
    if $rootScope.playerReady && typeof $routeParams.video != "undefined"

      $scope.videodata = _.find($scope.channel.videos.items, (video) ->
        video.id == $routeParams.video
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

  onPlayerReady = (event) ->
    event.target.playVideo()


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

  return
])
