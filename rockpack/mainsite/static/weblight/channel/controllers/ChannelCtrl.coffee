window.WebLite.controller('ChannelCtrl', ['$scope', '$routeParams', '$location', 'isMobile', 'channelData', 'userService', 'ContentService', '$rootScope', ($scope, $routeParams, $location, isMobile, channelData, userService, ContentService, $rootScope) ->

  $rootScope.channel = channelData
  $scope.page = 1
  $scope.getQueryVariable = (variable) ->
    query = window.location.search.substring(1)
    if (query.indexOf("&") > -1)
      vars = query.split("&")
    else
      vars = [query]
    for i in [0..vars.length-1]
      pair = vars[i].split("=")
      if(pair[0] == variable)
       return pair[1]
    return(false)


  $scope.triggerEvent = (action, label) ->
    ga('send', 'event', 'uiAction', action, label)

  $scope.coverRegex = new RegExp("channel/.*/")

  $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background_portrait/')

  $scope.channel.owner.avatar = channelData.owner.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_small')

  $scope.ChannelAvatar = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/thumbnail_small/')


  userID = $scope.getQueryVariable('shareuser')
  if userID?
    $scope.User = userService.fetchUser(userID)
      .then((data) ->
        data.avatar_thumbnail_url = data.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
        return data
      )

  $scope.showVideo = (videoObject, videoPos) ->
    $location.search({'video': videoObject.id})
    $rootScope.videoPosition = videoPos


  windowWidth = if "innerWidth" in window then window.innerWidth else document.documentElement.offsetWidth
  # Window Width is used to determine if this is a mobile view or not. Mobile does not autoplay the first video

  if not $routeParams.video? && windowWidth > 800
    $scope.showVideo($rootScope.channel.videos.items[0],0)

  selectedVideoID = $location.search().video
  if selectedVideoID? and selectedVideoID != true
    for videoObject in $scope.channel.videos.items
      if selectedVideoID == videoObject.id
        $scope.videodata = videoObject

  $scope.showPopup = true

  $scope.load_videos = () ->
    # Did we already load all the videos?
    if $scope.page*40 <= $scope.channel.videos.total
      ContentService.getChannelVideos(channelData.id, 40, $scope.page*40).then (data) =>
        $scope.channel.videos.items = $scope.channel.videos.items.concat(data.data.videos.items)
        $scope.page += 1
    return


  return
])
