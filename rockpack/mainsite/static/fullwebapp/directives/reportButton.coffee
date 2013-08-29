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
      scope.report = (reportObj) ->
        UserManager.Report(scope.objectId, scope.objectType, reportObj.myRadio.$modelValue)
        .then((data) ->
          if data.status == 204
            scope.showReportOverlay = false
            $rootScope.message = {
              message: "#{scope.objectType} has been reported"
              state: 0
            }
        )
  }
])