window.Weblight.controller('AppCtrl', ['$routeParams', 'isMobile', '$scope', '$location', ($routeParams, isMobile, $scope, $location) ->

  $scope.$watch((-> $location.url()), (newValue, oldValue) ->
    $scope.currentPage = newValue.substring(1)
  )

  $scope.isMobile = isMobile

  if isMobile
    $scope.isFindOutMoreOpen = true

  $scope.getWidth = ->
    return $(window).width()

  $scope.$watch($scope.getWidth, (newValue, oldValue) ->
    $scope.window_width = newValue
    return
  )

  window.onresize = ->
    $scope.$apply()

  $scope.wrapperWidth = ->
    # regular video size 235px, video margin 20px, container margin 60px
    # mobile video size 150px, video margin 5px, container margin 0px

    # Video size + margin + container margin
    if isMobile
      {width: Math.floor(($scope.window_width) / 150) * 150 + 'px'}
    else
      { width: Math.floor(($scope.window_width - 40 ) / 258) * 258 + 'px'}
])