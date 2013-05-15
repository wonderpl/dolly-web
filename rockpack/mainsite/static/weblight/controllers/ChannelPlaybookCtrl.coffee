window.Weblight.controller('ChannelPlaybookCtrl', ['$scope', 'browserServices', ($scope, browserServices) ->

  $scope.test = browserServices
  console.log $scope.test

  $scope.playbook = ["CREATE A CHANNEL", "CURATE A CHANNEL", "GROW YOUR SUBSCRIBERS", "EXPAND YOUR BRAND"]
  $scope.selectedChapter = "CREATE A CHANNEL"

  $scope.updateChapter = (chapter) ->
    $scope.selectedChapter = chapter
  return
])
