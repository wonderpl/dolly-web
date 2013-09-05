window.Weblight.controller('VideoCtrl', ['$scope', '$rootScope', '$routeParams', '$location', 'isMobile', 'userService', ($scope, $rootScope, $routeParams, $location, isMobile, userService) ->

  $scope.triggerEvent = (action, label) ->
    ga('send', 'event', 'uiAction', action, label)

  windowWidth = if "innerWidth" in window then window.innerWidth else document.documentElement.offsetWidth

  @getPlayerWidth = () ->
    if windowWidth <= 979
      @playerWidth = 300
      @playerHeight = 169
    else
      @playerWidth = 620
      @playerHeight = 349


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

  $scope.PlayVideo = =>
    if $rootScope.playerReady

      @getPlayerWidth()

      $scope.videodata = window.selected_video
      $scope.player = new YT.Player('player', {
        height: @playerHeight,
        width: @playerWidth,
        videoId: $scope.videodata.video.source_id,
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
#          'onReady': onPlayerReady,
          'onStateChange': onPlayerStateChange
        }

      })

  $scope.isSkeeping = false

  $scope.seekTo = (event) ->
    isSkeeping = true
    seekPosition = event.offsetX / 620
    $scope.player.seekTo($scope.player.getDuration() * seekPosition )
    $scope.player.playVideo()
    $scope.playerState = 1

#  onPlayerReady = (event) ->
#    $scope.player.mute()

  onPlayerStateChange = (event) ->
    $scope.playerState = event.data
    $scope.$apply()

    if event.data == 1
      setTimeout(trackProgress, 40)

  $scope.currentPosition = 0

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


  $scope.$watch((-> window.orientation), (newValue, oldValue) =>
    if oldValue != newValue
      @getPlayerWidth()
      $('#player').width(@playerWidth).height(@playerHeight)

  )

  $scope.$watch((-> $rootScope.playerReady), (newValue) ->
    if newValue
      $scope.PlayVideo()
    return
  )

  $scope.pausePlay = () ->
    if $scope.player.getPlayerState() == 1
      $scope.player.pauseVideo()
    else if $scope.player.getPlayerState() == 2
      $scope.player.playVideo()

  $scope.state = 'test'

  return
])