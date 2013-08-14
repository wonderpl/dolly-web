window.Weblight.controller('AppCtrl', ['$routeParams', 'isMobile', '$scope', '$location', '$rootScope', ($routeParams, isMobile, $scope, $location, $rootScope) ->

  $scope.isVertical = false

  $scope.$watch((-> $location.path()), (newValue, oldValue) ->
    $scope.currentPage = newValue.substring(1)
  )

  if typeof channel_data.category != "undefined"
    ga('send', 'pageview', {
      'dimension1':  channel_data.category
    })
  else
    ga('send', 'pageview')

  $scope.assets_url = assets_url
])