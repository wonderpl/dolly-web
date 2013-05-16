window.Weblight.controller('AppCtrl', ['$routeParams', 'isMobile', '$scope', '$location', '$rootScope', ($routeParams, isMobile, $scope, $location, $rootScope) ->

  $scope.$watch((-> $location.path()), (newValue, oldValue) ->
    $scope.currentPage = newValue.substring(1)
  )

  $scope.videoWidth = if isMobile then 150 else 218
  $scope.containerPadding = if isMobile then 0 else 40

  $scope.isMobile = isMobile

  if isMobile
    $scope.isFindOutMoreOpen = true

  $scope.getWidth = ->
    return $(window).width()

  window.onresize = ->
    $scope.$apply()

  $scope.$watch($scope.getWidth, (newValue, oldValue) ->
    $scope.windowWidth = { width: (Math.floor($(window).width() / $scope.videoWidth) * $scope.videoWidth + $scope.containerPadding) + 'px', margin: '0 auto'}
    return
  )

])