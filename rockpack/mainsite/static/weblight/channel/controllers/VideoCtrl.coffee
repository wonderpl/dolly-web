window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'isMobile', 'userService', ($scope, $rootScope, $routeParams, $location, isMobile, userService) ->

  $scope.triggerEvent = (action, label) ->
    ga('send', 'event', 'uiAction', action, label)

  $scope.currentPosition = 0
  windowWidth = if "innerWidth" in window then window.innerWidth else document.documentElement.offsetWidth

  $scope.getPlayerWidth = () ->
    if windowWidth < 600
      $scope.playerWidth = 320
    else
      if windowWidth < 1200
        $scope.playerWidth = 600
      else
        if windowWidth < 1600
          $scope.playerWidth = 800
        else
          $scope.playerWidth = 1000

    $scope.playerHeight = $scope.playerWidth*(9/16)

  $scope.PlayVideo = =>
    if $rootScope.playerReady && typeof $routeParams.video != "undefined"

      # ONLY USED FOR MOBILE VIDEO OVERLAY
      $rootScope.videoVisible = true
      $scope.getPlayerWidth()

      if $scope.player?
        $scope.player.loadVideoById($scope.videoObj.video.source_id)
      else
        $scope.player = new YT.Player('player', {
          height: $scope.playerHeight,
          width: $scope.playerWidth,
          videoId: $rootScope.videoObj.video.source_id,
          playerVars: {
            autoplay: 1,
            showinfo: 0,
            modestbranding: 1,
            wmode: "opaque",
            controls: 0,
            color: 'white',
            rel: 0,
            iv_load_policy: 3,
          },
          events: {
            'onStateChange': onPlayerStateChange
          }

        })

  $scope.isSkeeping = false

  $scope.seekTo = (event) ->
    isSkeeping = true
    offsetX = if event.offsetX then event.offsetX else event.clientX - $(event.target).offset().left
    console.log @playerWidth
    seekPosition = offsetX/$scope.playerWidth
    $scope.player.seekTo($scope.player.getDuration() * seekPosition )
    $scope.player.playVideo()
    $scope.playerState = 1

  onPlayerStateChange = (event) ->
    $scope.playerState = event.data
    $scope.$apply()
    if event.data == 1
      setTimeout(trackProgress, 40)
    else if event.data == 0
      if $rootScope.videoPosition < $rootScope.channel.videos.total
        $rootScope.videoPosition++
        $rootScope.videoObj = $rootScope.channel.videos.items[$rootScope.videoPosition]
        $location.search('video', $rootScope.videoObj)
        $rootScope.$apply()

  trackProgress = () ->
    if $scope.playerState == 1
      $scope.currentPosition = $scope.player.getCurrentTime()/$scope.player.getDuration()
      $scope.$apply()
      setTimeout(trackProgress, 40)


  $scope.hideOverlay = false

  setTimeout((->
    $scope.hideOverlay = true
  ), 100)

  $scope.mouseOver = () ->
    $scope.hideOverlay = false

  $scope.mouseOut = () ->
    $scope.hideOverlay = true


  $scope.$watch((-> $routeParams.video), (newValue) ->
    if newValue?
      if not $rootScope.videoPosition?
        tempIndex = 0
        $rootScope.videoObj = _.find($rootScope.channel.videos.items, (video) ->
          tempIndex++
          return video.id == $routeParams.video
        )
        $rootScope.videoPosition = tempIndex-1
      $rootScope.videoObj = $rootScope.channel.videos.items[$rootScope.videoPosition]
      $scope.PlayVideo()
    return
  )

  $scope.$watch((-> $rootScope.playerReady), (newValue) ->
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.pausePlay = () ->
    if $scope.playerState == 1
      $scope.player.pauseVideo()
    else if $scope.playerState == 2
      $scope.player.playVideo()


  $scope.shareFacebook = () ->
    FB.ui({
      method: 'feed',
      link: "http://rockpack.com/channel/#{$scope.channel.owner.id}/#{$scope.channel.id}/#",
      picture: $scope.channel.cover.thumbnail_url,
      name: 'Rockpack',
      caption: 'Shared a video with you'
    })

  $scope.shareTwitter = (url) ->
    window.open("http://twitter.com/intent/tweet?url=http://rockpack.com/channel/#{$scope.channel.owner.id}/#{$scope.channel.id}/#")

  getQueryVariable = (variable) ->
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

  $scope.userID = getQueryVariable('shareuser')

  $scope.user = userService.fetchUser($scope.userID)

  $scope.closeVideo = () ->
    $scope.player.stopVideo()
    $location.search('video', null)
    $rootScope.videoVisible = false


  return
])
