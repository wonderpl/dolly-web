window.Weblight.controller('ChannelCtrl', ['$scope', '$routeParams', '$location', 'isMobile', 'channelData', 'userService', ($scope, $routeParams, $location, isMobile, channelData, userService) ->

  $scope.channel = channelData

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

  height = if "innerHeight" in window then window.innerHeight else document.documentElement.offsetHeight
  width = if "innerWidth" in window then window.innerWidth else document.documentElement.offsetWidth
  calculatedPadding = (height - 32 - 322 - 227) / 2
  if calculatedPadding > 100
    $scope.pagePadding = calculatedPadding
  else
    $scope.pagePadding = 100


  $scope.coverRegex = new RegExp("channel/.*/")

  if width > 768
    $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background/')
  else
    $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background_portrait/')

  $scope.channel.owner.avatar = channelData.owner.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')


  userID = $scope.getQueryVariable('shareuser')
  if userID?
    $scope.User = userService.fetchUser(userID)
      .then((data) ->
        data.avatar_thumbnail_url = data.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
        return data
      )


  $scope.ChannelAvatar = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/thumbnail_small/')

  $scope.showVideo = (videoObject) ->
    $location.search({'video': videoObject.id})
    $scope.videodata = videoObject

  selectedVideoID = $location.search().video
  if selectedVideoID? and selectedVideoID != true
    for videoObject in $scope.channel.videos.items
      if selectedVideoID == videoObject.id
        $scope.videodata = videoObject

  $scope.showPopup = true

  $scope.load_videos = () ->
    console.log '******'
    # Did we already load all the videos?
    console.log $scope.channel.totalvideos
    if typeof $scope.channel.totalvideos == "undefined" or $scope.page*40 <= $scope.totalvideos
      ContentService.getChannelVideos($routeParams.userid, $routeParams.channelid, 40, $scope.page*40).then (data) =>
        if $scope.channel == null
          $scope.channel = data
          $scope.totalvideos = data.videos.total
          $scope.background = data.cover.thumbnail_url.replace('thumbnail_medium', 'background')
          console.log $scope.channel
        else
          $scope.channel.videos.items = $scope.channel.videos.items.concat(data.videos.items)
        $scope.page += 1
    return


  return
])
