# TODO: Currently the overlay is part of each cell, which adds unneccesry elements for each video cell. Should be moved globally
angular.module('WebApp').directive('videoCell', [ '$location', '$dialog', 'UserManager', ($location, $dialog, UserManager) ->
  return {
    restrict: 'E'
    templateUrl: 'videoCell.html'
    controller: ($scope) ->
      if UserManager.isLoggedIn
        $scope.isloggedIn = true

      $scope.setCurrentVideo = (video) ->
        $location.search( 'video', video.id )

      $scope.addToFavourites = (videoid) ->
        for channel in UserManager.details.channels.items
          if channel.favourites?
            UserManager.addVideo(channel.resource_url,videoid)

      $scope.addToChannel = (videoId) ->
        dialog = $dialog.dialog(
          controller: 'AddtoChannelCtrl',
          resolve: {
            videoId: () ->
             return videoId
          }
        )
        dialog.open('addtochannel.html')
        link: (scope, elem, attrs) ->
      return
  }
])