window.Weblight.controller('ChannelCtrl', ['$scope', '$rootScope', 'ContentService', ($scope, $rootScope, ContentService) ->

  $scope.channel = window.channel_data
  $scope.totalvideos = $scope.channel.videos.total
  $scope.page = 1
  $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')

  $scope.playVideo = (videoPos) ->
    $rootScope.videoPosition = videoPos

  $scope.load_videos = () ->
    if $scope.page*40 <= $scope.totalvideos
      ContentService.getChannelVideos(40, $scope.page*40).then ((data) ->
        $scope.channel.videos.items = $scope.channel.videos.items.concat(data.videos.items)
        $scope.page += 1
      )

  $scope.shareFacebook = () ->
    FB.ui({
      method: 'feed',
      link: "http://www.rockpack.com/channel/#{$scope.channel.owner.id}/#{$scope.channel.id}/#",
      picture: $scope.channel.cover.thumbnail_url,
      name: 'Rockpack',
      caption: 'Shared a video with you'
    })

  $scope.shareTwitter = (url) ->
    window.open("http://twitter.com/intent/tweet?url=http://www.rockpack.com/channel/#{$scope.channel.owner.id}/#{$scope.channel.id}/#")

])
