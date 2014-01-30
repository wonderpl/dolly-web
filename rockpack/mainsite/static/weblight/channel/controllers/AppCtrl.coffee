window.WebLite.controller('AppCtrl', ['$routeParams', 'isMobile', '$scope', '$location', '$rootScope', '$window', ($routeParams, isMobile, $scope, $location, $rootScope, $window) ->

  $scope.$watch((-> $location.path()), (newValue, oldValue) ->
    $scope.currentPage = newValue.substring(1)
  )

  $scope.getHeight = () ->
   return $(window).height()

  $scope.$watch($scope.getHeight, (newValue, oldValue) ->
    $scope.documentHeight = newValue
    $scope.channelHeight = newValue - 450 - 64
  )

  window.onresize = () ->
    $scope.$apply()


  if typeof channel_data.category != "undefined"
    ga('send', 'pageview', {
      'dimension1':  channel_data.category
    })
  else
    ga('send', 'pageview')

  $scope.assets_url = assets_url

])

