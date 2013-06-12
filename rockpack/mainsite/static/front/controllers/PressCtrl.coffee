window.contentApp.controller('PressCtrl', ['$scope', ($scope) ->

  $scope.categories = ["PRESS COVERAGE", "PRESS RELEASES", "LOGOS & BRAND", "CONTACT"]
  $scope.selectedChapter = "PRESS COVERAGE"

  $scope.updateChapter = (chapter) ->
    $scope.selectedChapter = chapter

  $scope.assets_url = window.assets_url
])
