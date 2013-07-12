window.contentApp.controller('PressCtrl', ['$scope', '$location', ($scope, $location) ->

  $scope.categories = ["PRESS", "PARTNERS", "LOGOS & BRAND", "CONTACT"]
  $scope.selectedChapter = "PRESS"

  $scope.updateChapter = (chapter) ->
    $location.search('section', chapter)

  $scope.assets_url = window.assets_url

  $scope.$watch(( () ->
    return $location.search().section
  ), (newValue, oldValue) ->
    if $scope.categories.indexOf(newValue.toUpperCase()) > -1
      $scope.selectedChapter = newValue.toUpperCase()
    else
      $scope.selectedChapter = "PRESS"
  )


])
