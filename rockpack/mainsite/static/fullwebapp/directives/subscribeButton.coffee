angular.module('WebApp').directive('subscribeButton', (UserManager ) ->
  return {
    restrict: 'A',
    templateUrl: 'subscribeButton.html'
    link: (scope, elem, attrs) ->
      console.log("Recognized the fundoo-rating directive usage")
      console.log UserManager
  }
)