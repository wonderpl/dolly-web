# TODO: Handle direct links to video (video data has not been loaded yet)
# TODO: Handle screen resize while video playing (on sidebar - as there are two sidebar sizes)

window.WebApp.controller('VideoPlayerCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'playerService', ($scope, $rootScope, $routeParams, $location, playerService) ->

  $scope.playerSize = {
    main: {
      width: 860,
      height: 484
    },
    sideBig: {
      width: 356,
      height: 200
    }
    sideSmall: {
      width: 242,
      height: 136
    }
  }

  $scope.PlayVideo = () =>
    if $rootScope.playerReady && playerService.getVideo()?

      $scope.video = playerService.getVideo()
      $scope.channel = playerService.getChannel()

      if $scope.player?
        $scope.player.loadVideoById($scope.video.video.source_id)
      else
        $scope.player = new YT.Player('player', {
          height: 484,
          width: 860,
          videoId: $scope.video.video.source_id,
          playerVars: {
            autoplay: 1,
            showinfo: 0,
            modestbranding: 1,
            wmode: "opaque",
            controls: 1,
            cc_load_policy: 0,
            fs: 1,
            iv_load_policy: 3,
            rel: 0,

          }
        })

  $scope.$watch((-> playerService.getVideo()), (newValue) ->
    if newValue != null
      $scope.PlayVideo()
    else
      if $scope.player?
        $scope.player.stopVideo()
  )

  $scope.$watch((-> playerService.getLocation()), (newValue, oldValue) ->
    if newValue == 1
      $scope.player.setSize($scope.playerSize.main.width, $scope.playerSize.main.height)
    else if newValue == 2
      if $scope.sidebarWidth == 246
        $scope.player.setSize($scope.playerSize.sideSmall.width, $scope.playerSize.sideSmall.height)
      else
        $scope.player.setSize($scope.playerSize.sideBig.width, $scope.playerSize.sideBig.height)
    $scope.playerLocation = newValue
  )

  $scope.$watch((-> $rootScope.playerReady), (newValue) ->
    if newValue?
      $scope.PlayVideo()
  )

#  $scope.$watch((() -> return $location.search().video), (newValue, oldValue) ->
#    if newValue?
#      $scope.PlayVideo($routeParams.video)
#  )


  $scope.minimize = () ->
     playerService.setLocation(2)

  $scope.close = () ->
    playerService.closePlayer()


  return
])
