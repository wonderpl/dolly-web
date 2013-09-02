#NOT IN Used, partial capabilities of channel editing. Removed from Medium web
window.WebApp.controller('EditChannelCtrl', ['$scope', '$routeParams', '$rootScope', '$location', 'ContentService', '$dialog', 'UserManager', 'shareService', 'categoryService', ($scope, $routeParams, $rootScope, $location, ContentService, $dialog, UserManager, shareService, categoryService) ->

  #TODO: Pass video added to channel creation process (can pass id, but won't be playable)

  $scope.page = 0
  $scope.User = UserManager
  $scope.channel = {}
  $scope.coverArt = {
    visible: false
    data: {}
    position: 0
  }

  $scope.categories = categoryService.fetchCategories()



  $scope.load_videos = =>
    # Did we already load all the videos? Only needed when editing an existing channel
    if (typeof $scope.totalvideos == "undefined" or $scope.page*40 <= $scope.totalvideos) and $routeParams.channelid?
      ContentService.getChannelVideos($routeParams.userid, $routeParams.channelid, 40, $scope.page*40).then (data) =>
        if $scope.channel == null
          $scope.channel = data
          $scope.totalvideos = data.videos.total
          $scope.background = data.cover.thumbnail_url.replace('thumbnail_medium', 'background')
        else
          $scope.channel.videos.items = $scope.channel.videos.items.concat(data.videos.items)
        $scope.page += 1
    return

  $scope.coverSelector = () ->
    $scope.coverArt.visible = true
    if not $scope.coverArt.data.cover_art?
      ContentService.getCoverArt()
        .then((data) ->
          $scope.coverArt.data = data
          $scope.coverArt.position += 1
        )

  $scope.selectCover = (cover) ->
    console.log cover
    $("#bgimage").attr("src", cover.thumbnail_url.replace("thumbnail_medium", "background"))
    $scope.coverArt.visible = false

  $scope.load_covers = () ->
    if $scope.coverArt.visible == true and $scope.coverArt.data.cover_art.total > $scope.coverArt.position*50
      ContentService.getCoverArt($scope.coverArt.position*50)
        .then((data) ->
          $scope.coverArt.data.cover_art.items = $scope.coverArt.data.cover_art.items.concat(data.cover_art.items)
          $scope.coverArt.position += 1
        )
  return


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
