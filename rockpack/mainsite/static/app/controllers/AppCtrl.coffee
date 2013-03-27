window.Weblight.controller('AppCtrl', ['$routeParams', 'isMobile', '$scope', ($routeParams, isMobile, $scope) -> 

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
    console.log $scope.window_width
    if isMobile
      {width: Math.floor(($scope.window_width) / 150) * 150 + 'px'}
    else
      { width: Math.floor(($scope.window_width - 40 ) / 235) * 235 + 'px'}
])