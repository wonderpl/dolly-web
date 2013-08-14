window.Weblight.controller('ChannelCtrl', ['$scope', '$routeParams', '$location', 'isMobile', 'channelData', 'userService', ($scope, $routeParams, $location, isMobile, channelData, userService) ->

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

  $scope.channel = channelData

  $scope.channel.owner.avatar = channelData.owner.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')

  $scope.coverRegex = new RegExp("channel/.*/")

  userID = $scope.getQueryVariable('shareuser')
  if userID?
    $scope.User = userService.fetchUser(userID)
      .then((data) ->
        data.avatar_thumbnail_url = data.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
        return data
      )

  $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/background/')
  $scope.ChannelAvatar = $scope.channel.cover.thumbnail_url.replace($scope.coverRegex, 'channel/thumbnail_small/')


  height = if "innerHeight" in window then window.innerHeight else document.documentElement.offsetHeight
  calculatedPadding = (height - 32 - 322 - 227) / 2
  if calculatedPadding > 100
    $scope.pagePadding = calculatedPadding
  else
    $scope.pagePadding = 100

  $scope.showVideo = (videoObject) ->
    $location.search({'video': videoObject.id})
    $scope.videodata = videoObject

  selectedVideoID = $location.search().video
  if selectedVideoID? and selectedVideoID != true
    for videoObject in $scope.channel.videos.items
      if selectedVideoID == videoObject.id
        $scope.videodata = videoObject

  $scope.showPopup = true

  return
])
