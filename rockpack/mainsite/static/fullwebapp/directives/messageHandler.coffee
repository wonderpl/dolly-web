angular.module('WebApp').directive('messageHandler', [ '$rootScope', ($rootScope) ->
  return {
    restrict: 'E'
    template: '<div id="message" class="alert" style="display: none">{{message.message}}</div>'
    link: (scope, elm, attrs) ->

      $rootScope.$watch('message', (newValue, oldValue) ->
        if newValue?
          scope.showMessage()
          setTimeout((
            () ->
              scope.hideMessage()
          ),5000)
      )

      scope.showMessage = () ->
        $("#message").show('fast')

      scope.hideMessage = () ->
        $("#message").hide('fast')
        $rootScope.message = {}

      return
  }
])