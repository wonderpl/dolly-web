window.WebApp.controller('FeedCtrl', ['$scope', 'cookies', 'UserManager', '$location', '$dialog', ($scope, cookies, UserManager, $location, $dialog) ->

  $scope.User = UserManager

  $scope.load_feed = () ->
    if ($scope.User.feed.total == null or $scope.User.feed.total > $scope.User.feed.position)
      $scope.User.FetchRecentSubscriptions($scope.User.feed.position, 50)
      $scope.User.feed.position += 50

  $scope.setCurrentVideo = (video) ->
    $location.search( 'video', video.id )

  $scope.$watch((() -> return $location.search().video), (newValue, oldValue) ->
    if newValue?

      dialog = $dialog.dialog(
        controller: 'VideoPlayerCtrl',
        resolve: {
          ChannelData: () ->
            #TODO fix ugly hack
            flatarray = []
            _.each($scope.User.feed.items, (date) ->
              flatarray = flatarray.concat(flatarray, date.videos)
            )
            return {videos:{items:flatarray}}
        }
      )

      dialog.open('videoPlayer.html').then(() ->
        $location.search( 'video', null )
      )
  )
])
