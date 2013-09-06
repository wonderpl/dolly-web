window.Weblight.controller('ChannelCtrl', ['$scope', '$routeParams', '$location', 'channelData', '$rootScope', ($scope, $routeParams, $location, channelData, $rootScope) ->

  $scope.channel = channelData
  $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')

  $scope.playVideo = (videoid) ->
  	$rootScope.currVideo = videoid 
  return
])
