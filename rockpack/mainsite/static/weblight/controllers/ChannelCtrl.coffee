window.Weblight.controller('ChannelCtrl', ['$scope', '$routeParams', '$location', 'isMobile', 'channelData', ($scope, $routeParams, $location, isMobile, channelData) ->

  $scope.triggerEvent = (action, label) ->
    ga('send', 'event', 'uiAction', action, label)

  $scope.isMobile = isMobile
  $scope.channel = channelData

  $scope.channel.owner.avatar = channelData.owner.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')

  $scope.coverRegex = new RegExp("channel/.*/")


  $scope.$watch('isVertical', (newValue, oldValue) ->
    if $scope.isVertical
      $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background_portrait/')
    else
      $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background/')
  )

  $scope.iphonebg = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background_portrait/')

  # Additional defaults
  $scope.videoCellTitleLength = if $scope.isMobile then 40 else 50
  $scope.channelTitleLength = if $scope.isMobile then 15 else 25

  # Catch share of specific video url
  $scope.url = $location.absUrl()
  if($scope.url.substr(-1) == '/')
    $scope.url = $scope.url.substr(0, $scope.url.length - 1)



  if selected_video != null
#    $location.search( 'video',selected_video.id)
    $scope.sharetext = "has shared a video with you from a channel on Rockpack."
  else
    $scope.sharetext = "has shared a video channel with you on Rockpack."

  return
])
