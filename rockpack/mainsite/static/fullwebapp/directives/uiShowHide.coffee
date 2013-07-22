angular.module('WebApp').directive('uiShow', [() ->
  return (scope, elm, attrs) ->
    scope.$watch(attrs.uiShow, (newVal, oldVal) ->
      if (newVal)
        elm.addClass('ui-show')
      else
        elm.removeClass('ui-show')
    )
])

angular.module('WebApp').directive('uiHide', [ () ->
  return (scope, elm, attrs) ->
    scope.$watch(attrs.uiHide, (newVal, oldVal) ->
      if (newVal)
        elm.addClass('ui-hide')
      else
        elm.removeClass('ui-hide')
    )
])
