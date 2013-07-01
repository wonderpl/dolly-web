angular.module('WebApp').directive('videoCell', ['UserManager', '$route', (UserManager, $route) ->
  return {
    restrict: 'A'
    templateUrl: 'subscribeButton.html'
    controller: ($scope) ->

    link: (scope, elem, attrs) ->
      return
  }
])