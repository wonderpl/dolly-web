window.WebApp.controller('ChannelCtrl', ['$scope', '$routeParams', '$rootScope', '$location', 'ContentService', '$dialog', 'UserManager', 'shareService', ($scope, $routeParams, $rootScope, $location, ContentService, $dialog, UserManager, shareService) ->

  $scope.page = 0
  $scope.User = UserManager
  $scope.channel = null

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

  # Video Player
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

  #Variable width manager
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
