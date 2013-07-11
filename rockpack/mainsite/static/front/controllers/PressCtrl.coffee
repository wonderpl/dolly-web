window.contentApp.controller('PressCtrl', ['$scope', ($scope) ->

  $scope.categories = ["PRESS", "PARTNERS", "LOGOS & BRAND", "CONTACT"]
  $scope.selectedChapter = "PRESS"

  $scope.updateChapter = (chapter) ->
    $scope.selectedChapter = chapter

  $scope.assets_url = window.assets_url
])
