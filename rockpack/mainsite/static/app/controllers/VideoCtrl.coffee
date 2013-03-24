window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', ($scope, $rootScope, $routeParams, $location) ->

  # $scope.getPlayerReady = -> 
  #   return $rootScope.playerReady

  # $scope.$watch($scope.getPlayerReady, (newValue) ->
  #   if newValue
  #     $scope.playVideo()
  #   return
  # )

  console.log $scope

  # $scope.playVideo = ->
  #   if typeof $routeParams.videoid != "undefined" and $rootScope.playerReady
  #     $scope.videodata = _.find($rootScope.videos, (video) -> 
  #       video.id == $routeParams.videoid
  #     )
  #     $scope.player = new YT.Player('player', {
  #       height: '415',
  #       width: '738',
  #       videoId: $scope.videodata.video.source_id,
  #       playerVars: {
  #         autoplay: 1,
  #         showinfo: 0,
  #         modestbranding: 0
  #       }
  #     })


  # $scope.$watch((-> return $('#player').length == 1), (newValue) ->
  #   if newValue
  #     $scope.playVideo()
  # )

  # # $scope.open = ->


  # $scope.close = ->
  #   # $scope.player.stopVideo()
  #   $scope.shouldBeOpen = false
  #   $location.search( 'videoid', null )
  #   return

  return
])
