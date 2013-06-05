angular.module('WebApp').directive('infinityScroll', () ->

  return {
    restrict: "A",
    transclude: true,

    link: (scope, elm, $attrs) ->
      listView = new infinity.ListView($(elm), {
        lazy: () ->
          $(this).find("[infinity-item]").each(() ->
            $ref = $(this)
            $ref.attr('src', $ref.attr('data-original'))
          )
        useElementScroll: true
      })
      elm.data("listView", listView)
  }
)

angular.module('WebApp').directive('infinityItem', () ->

  return {
    restrict: "A",
    link: (scope, element, attrs) ->
      listView = $("#" + attrs.infinityItem).data("listView")
      if (listView)
        listView.append(element)
  }
)