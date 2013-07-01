angular.module('WebApp').directive('videoCell', [ '$location', '$dialog', ($location, $dialog) ->
  return {
    restrict: 'E'
    templateUrl: 'videoCell.html'
    controller: ($scope) ->

      $scope.setCurrentVideo = (video) ->
        $location.search( 'video', video.id )

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