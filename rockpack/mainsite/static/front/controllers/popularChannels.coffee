window.contentApp.controller('popularChannels', ['$scope', '$location', ($scope, $location) ->
  $scope.channels = window.top_channels.channels

  $scope.show = (channelid, userid) ->
    window.location = "http://#{$location.host()}/channel/#{userid}/#{channelid}/"

])
