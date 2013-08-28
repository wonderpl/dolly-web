# No Longer in use, functions assigned directly to controllers.
angular.module('WebApp').directive('videoCell', [ '$location', '$dialog', 'UserManager', ($location, $dialog, UserManager) ->
  return {
    restrict: 'E'
    templateUrl: 'videoCell.html'
    controller: ($scope) ->

#     Hide Add to channel/Favorites if user is not logged in
      if UserManager.isLoggedIn
        $scope.isloggedIn = true

      $scope.setCurrentVideo = (video) ->
        if video.displayOverlay == false
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