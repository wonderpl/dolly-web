window.contentApp.controller('ChannelPlaybookCtrl', ['$scope', ($scope) ->

  $scope.playbook = ["CREATE A CHANNEL", "CURATE A CHANNEL", "GROW YOUR SUBSCRIBERS", "EXPAND YOUR BRAND"]
  $scope.selectedChapter = "CREATE A CHANNEL"

  $scope.updateChapter = (chapter) ->
    $scope.selectedChapter = chapter

])
