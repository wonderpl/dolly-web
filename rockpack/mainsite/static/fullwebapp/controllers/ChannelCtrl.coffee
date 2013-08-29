window.WebApp.controller('ChannelCtrl', ['$scope', '$routeParams', '$rootScope', '$location', 'ContentService', '$dialog', 'UserManager', 'shareService', 'playerService', ($scope, $routeParams, $rootScope, $location, ContentService, $dialog, UserManager, shareService, playerService) ->

  $scope.page = 0
  $scope.User = UserManager
  $scope.channel = null
  $scope.currentUrl = encodeURIComponent($location.absUrl())


  $scope.load_videos = =>
    # Did we already load all the videos?
    if typeof $scope.totalvideos == "undefined" or $scope.page*40 <= $scope.totalvideos
      ContentService.getChannelVideos($routeParams.userid, $routeParams.channelid, 40, $scope.page*40).then (data) =>
        if $scope.channel == null
          $scope.channel = data
          $scope.totalvideos = data.videos.total
          $scope.background = data.cover.thumbnail_url.replace('thumbnail_medium', 'background')
        else
          $scope.channel.videos.items = $scope.channel.videos.items.concat(data.videos.items)
        $scope.page += 1
    return

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

  $scope.setCurrentVideo = (video) ->
    playerService.setNewPlaylist($scope.channel, video.id, 1)
    $location.search( 'video', video.id )

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


  $scope.playAll = () ->

    playerService.setNewPlaylist($scope.channel, $scope.channel.videos.items[0].id, 1)
    $location.search( 'video', $scope.channel.videos.items[0].id )
])
