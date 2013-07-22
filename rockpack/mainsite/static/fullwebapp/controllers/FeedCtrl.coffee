window.WebApp.controller('FeedCtrl', ['$scope', 'cookies', 'UserManager', '$location', '$dialog', ($scope, cookies, UserManager, $location, $dialog) ->

  console.log 'in Feed'

  $scope.User = UserManager
  $scope.User.feed.total = null
  $scope.User.feed.position = 0
  $scope.User.feed.items = []

  $scope.load_feed = () ->
    if ($scope.User.feed.total == null or $scope.User.feed.total > $scope.User.feed.position*50)
      $scope.User.FetchRecentSubscriptions($scope.User.feed.position*50, 50)
      $scope.User.feed.position += 1

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

  $scope.videoWidth = 340
  $scope.containerPadding = 0

  $scope.getWidth = ->
   return $(window).width()

  window.onresize = ->
    $scope.$apply()

  $scope.$watch($scope.getWidth, (newValue, oldValue) ->
    $scope.videwWrapperWidth = { width: (Math.floor(($(window).width() - $scope.containerPadding) / $scope.videoWidth) * $scope.videoWidth + $scope.containerPadding) + 'px', margin: '0 auto'}
    return
  )

])
