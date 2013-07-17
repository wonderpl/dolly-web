window.WebApp.controller('SearchCtrl', ['$scope', 'SearchService', '$q', '$location', '$dialog', ($scope, SearchService, $q, $location, $dialog) ->

  $scope.$watch((() -> return $location.search().search), (newValue, oldValue) ->
    if newValue?
      SearchService.videoSearch(newValue, 0, 50)
        .success((data) ->
          $scope.videos = data
        )
      SearchService.channelSearch(newValue, 0, 50)
        .success((data) ->
          $scope.channels = data
        )
      SearchService.userSearch(newValue, 0, 50)
        .success((data) ->
          $scope.users = data
        )

      $scope.position = {
        videos: 50,
        channels: 50,
        users: 50
      }
  )

  $scope.setCurrentVideo = (video) ->
    $location.search( 'video', video.id )

  $scope.$watch((() -> return $location.search().video), (newValue, oldValue) ->
    if newValue?

      dialog = $dialog.dialog(
        controller: 'VideoPlayerCtrl',
        resolve: {
          ChannelData: () ->
            return $scope.videos
        }
      )

      dialog.open('videoPlayer.html').then(() ->
        $location.search( 'video', null )
      )
  )

  $scope.load_videos = () ->
    if $scope.videos?
      SearchService.videoSearch($location.search().search, $scope.position.videos, 50)
      .success((data) ->
          $scope.videos.videos.items = $scope.videos.videos.items.concat(data.videos.items)
          $scope.position.videos += 50
      )

  $scope.load_channels = () ->
    if $scope.channels?
      SearchService.channelSearch($location.search().search, $scope.position.videos, 50)
        .success((data) ->
          $scope.channels.channels.items = $scope.channels.channels.items.concat(data.channels.items)
          $scope.position.channels += 50
        )


  $scope.load_users = () ->
    if $scope.users?
      SearchService.userSearch($location.search().search, $scope.position.videos, 50)
        .success((data) ->
          $scope.users.users.items = $scope.users.users.items.concat(data.users.items)
          $scope.position.users += 50
        )

])
