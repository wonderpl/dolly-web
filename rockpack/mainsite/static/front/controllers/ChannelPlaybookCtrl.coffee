window.contentApp.controller('ChannelPlaybookCtrl', ['$scope', ($scope) ->

  _gaq.push(['_trackPageview', 'Channel Playbook'])

  $scope.playbook = ["CREATE A CHANNEL", "CURATE A CHANNEL", "GROW YOUR SUBSCRIBERS", "EXPAND YOUR BRAND"]
  $scope.selectedChapter = "CREATE A CHANNEL"

  $scope.updateChapter = (chapter) ->
    $scope.selectedChapter = chapter
  return
])
