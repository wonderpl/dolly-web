window.Weblight.controller('AppCtrl', ['$routeParams', 'isMobile', '$scope', '$location', '$rootScope', ($routeParams, isMobile, $scope, $location, $rootScope) ->

  $scope.isVertical = false

  $scope.$watch((-> $location.path()), (newValue, oldValue) ->
    $scope.currentPage = newValue.substring(1)
  )

#  isMobile = true

  $scope.videoWidth = if isMobile then 285 else 306
  $scope.containerPadding = if isMobile then 30 else 40

  $scope.isMobile = isMobile

  if isMobile
    $scope.isFindOutMoreOpen = true

  $scope.getWidth = ->
    return $(window).width()

  window.onresize = ->
    $scope.$apply()

  $scope.$watch($scope.getWidth, (newValue, oldValue) ->
    $scope.windowWidth = { width: (Math.floor(($(window).width() - $scope.containerPadding) / $scope.videoWidth) * $scope.videoWidth + $scope.containerPadding) + 'px', margin: '0 auto'}
    if newValue < 768
      $scope.isVertical = true
    else
      $scope.isVertical = false
    return
  )

  if typeof channel_data.category != "undefined"
    ga('send', 'pageview', {
      'dimension1':  channel_data.category
    })
  else
    ga('send', 'pageview')

  $scope.assets_url = assets_url
  $scope.full_path = window.full_path

])