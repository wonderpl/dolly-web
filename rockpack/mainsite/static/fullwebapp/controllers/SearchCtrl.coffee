window.WebApp.controller('SearchCtrl', ['$scope', 'SearchService', '$q', '$location', '$dialog', ($scope, SearchService, $q, $location, $dialog) ->

  $scope.searchresults = (searchPhrase) ->
    SearchService.suggest(searchPhrase)

  $scope.fetchresults = () ->
    $location.search( 'search', $scope.searchPhrase )

  $scope.$watch((() -> return $location.search().search), (newValue, oldValue) ->
    if newValue?
      $scope.videos = SearchService.videoSearch(newValue, 0, 5)
      $scope.channels = SearchService.channelSearch($scope.searchPhrase, 0, 50)
  )

  $scope.setCurrentVideo = (video) ->
    $location.search( 'video', video.id )

  $scope.$watch((() -> return $location.search().video), (newValue, oldValue) ->
    if newValue?

      console.log newValue
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
])
