window.Weblight.controller('ChannelCtrl', ['$scope', '$routeParams', '$location', 'channelData', ($scope, $routeParams, $location, channelData) ->

  $scope.channel = channelData
  $scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
  return
])
