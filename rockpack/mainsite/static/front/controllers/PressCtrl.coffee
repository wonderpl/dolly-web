window.contentApp.controller('PressCtrl', ['$scope', ($scope) ->

  $scope.categories = ["PARTNERS", "PRESS", "LOGOS & BRAND", "CONTACT"]
  $scope.selectedChapter = "PARTNERS"

  $scope.updateChapter = (chapter) ->
    $scope.selectedChapter = chapter

  $scope.assets_url = window.assets_url
])
