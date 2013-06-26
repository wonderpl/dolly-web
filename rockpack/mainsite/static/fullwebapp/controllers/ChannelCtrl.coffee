window.WebApp.controller('ChannelCtrl', ['$scope', '$routeParams', '$rootScope', '$location', 'ContentService', '$dialog', 'UserManager', ($scope, $routeParams, $rootScope, $location, ContentService, $dialog, UserManager) ->

  $scope.page = 0
  $scope.User = UserManager
  $scope.channel = null

  $scope.load_videos = =>
    #only try to fech videos if there are hidden videos in the channel
    if typeof $scope.totalvideos == "undefined" or $scope.page*40 <= $scope.totalvideos
      ContentService.getChannelVideos($routeParams.userid, $routeParams.channelid, 40, $scope.page*40).then (data) =>
        if $scope.channel == null
          $scope.channel = data
          $scope.totalvideos = data.videos.total
        else
          $scope.channel.videos.items = $scope.channel.videos.items.concat(data.videos.items)
        console.log $scope.channel
        $scope.page += 1
    return


  $scope.setCurrentVideo = (video) ->
    $location.search( 'video', video.id )

  $scope.$watch((() -> return $location.search().video), (newValue, oldValue) ->
    if newValue?
      d = $dialog.dialog({resolve: () ->
        return $scope.channel
      })
      d.open('videoPlayer.html').then(() ->
        $location.search( 'video', null )
      )
  )

  $scope.addToChannel = (videoId) ->
    d = $dialog.dialog({resolve: () ->
      return videoId
    })
    d.open('addtochannel.html')
])
