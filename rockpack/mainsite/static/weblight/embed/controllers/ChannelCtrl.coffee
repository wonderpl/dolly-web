window.Weblight.controller('ChannelCtrl', ['$scope', '$routeParams', '$location', 'channelData', '$rootScope', ($scope, $routeParams, $location, channelData, $rootScope) ->

	$scope.channel = channelData
	$scope.channel.cover.thumbnail_url = $scope.channel.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')

	$scope.playVideo = (videoid) ->
		$rootScope.currVideo = videoid 

	$scope.shareFacebook = () ->
		FB.ui({
			method: 'feed',
			link: "http://www.rockpack.com/channel/#{$scope.channel.owner.id}/#{$scope.channel.id}/#",
			picture: $scope.channel.cover.thumbnail_url,
			name: 'Rockpack',
			caption: 'Shared a video with you'
		})

	$scope.shareTwitter = (url) ->
		window.open("http://twitter.com/intent/tweet?url=http://www.rockpack.com/channel/#{$scope.channel.owner.id}/#{$scope.channel.id}/#")

])
