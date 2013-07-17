window.WebApp.controller('ChannelCtrl', ['$scope', '$routeParams', '$rootScope', '$location', 'ContentService', '$dialog', 'UserManager', 'shareService', ($scope, $routeParams, $rootScope, $location, ContentService, $dialog, UserManager, shareService) ->

  $scope.page = 0
  $scope.User = UserManager
  $scope.channel = null

  $scope.load_videos = =>
    #only try to fech videos if there are hidden videos in the channel
    if typeof $scope.totalvideos == "undefined" or $scope.page*40 <= $scope.totalvideos
      console.log 'load videos'
      ContentService.getChannelVideos($routeParams.userid, $routeParams.channelid, 40, $scope.page*40).then (data) =>
        if $scope.channel == null
          $scope.channel = data
          $scope.totalvideos = data.videos.total
          $scope.background = data.cover.thumbnail_url.replace('thumbnail_medium', 'background')
        else
          $scope.channel.videos.items = $scope.channel.videos.items.concat(data.videos.items)
        $scope.page += 1
    return

  $scope.$watch((() -> return $location.search().video), (newValue, oldValue) ->
    if newValue?

      dialog = $dialog.dialog(
        controller: 'VideoPlayerCtrl',
        resolve: {
          ChannelData: () ->
            return $scope.channel
        }
      )

      dialog.open('videoPlayer.html').then(() ->
        $location.search( 'video', null )
      )
  )

  $scope.share = (method, shareid) ->
    shareService.fetchShareUrl('channel', shareid)
    .success((data) ->
      if method == "facebook"
        FB.ui({
          method: 'feed',
          link: data.resource_url,
          picture: $scope.background,
          name: 'Rockpack',
          caption: data.message
        })
    )

])
