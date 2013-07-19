angular.module('WebApp').directive('reportButton', ['UserManager', (UserManager) ->
  return {
    restrict: 'A'
    templateUrl: 'reportButton.html'
    scope: {
      isLoggedin: '@' ,
      objectId: '@',
      objectType: '@',
      test: '@'
    },
    link: (scope, element, attrs) ->
      console.log scope.test
      scope.report = () ->
        UserManager.report(scope.objectID, scope.objectType)
  }
])