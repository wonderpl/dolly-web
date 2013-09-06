window.WebApp.controller('videoShareCtrl', ['$scope','UserManager', 'videoShareService', '$dialog', '$location', ($scope, UserManager, videoShareService, $dialog, $location) ->

  $scope.$watch((() -> UserManager.isLoggedIn), (newValue, oldValue) ->
    $scope.isLoggedIn = newValue
  )

  $scope.$watch((() -> videoShareService.getVideoObj()), (newValue, oldValue) ->
    $scope.video = newValue
  )

  $scope.showShare = false

  #Video Specific Functions
  $scope.shareFacebook = (video) ->
    FB.ui({
      method: 'feed',
      link: $location.absUrl(),
      picture: video.video.thumbnail_url,
      name: 'Rockpack',
      caption: 'Shared a video with you'
    })

  $scope.shareTwitter = (url) ->
    window.open("http://twitter.com/intent/tweet?url=#{url}")

  $scope.addToFavourites = (videoid) ->
    for channel in UserManager.details.channels.items
      if channel.favourites?
        UserManager.addVideo(channel.resource_url,videoid)

  $scope.addToChannel = (videoId) ->
    dialog = $dialog.dialog(
      controller: 'AddtoChannelCtrl',
      resolve: {
        videoId: () ->
          return videoId
        }
    )
    dialog.open('addtochannel.html')
      link: (scope, elem, attrs) ->

])