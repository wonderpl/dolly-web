window.Weblight.controller('AppCtrl', ['$routeParams', 'isMobile', '$scope', ($routeParams, isMobile, $scope) -> 
  $scope.getWidth = ->
    return $(window).width()

  $scope.$watch($scope.getWidth, (newValue, oldValue) ->
    $scope.window_width = newValue
    return
  )

  window.onresize = ->
    $scope.$apply()

  $scope.wrapperWidth = ->
    # Video size 215 + 20px margin + 60px container margin

    return {
      width: Math.floor(($scope.window_width - 40 ) / 235) * 235 + 'px'
    }
])