angular.module('WebApp').directive('reportButton', ['UserManager', '$rootScope', (UserManager, $rootScope) ->
  return {
    restrict: 'A'
    templateUrl: 'reportButton.html'
    scope: {
      isLoggedin: '@'
      objectId: '@'
      objectType: '@'
    },
    link: (scope, element, attrs) ->
      scope.report = () ->
        UserManager.Report(scope.objectId, scope.objectType)
        .then((data) ->
          if data.status == 204
            $rootScope.message = {
              message: "#{scope.objectType} has been reported"
              state: 0
            }
        )
  }
])