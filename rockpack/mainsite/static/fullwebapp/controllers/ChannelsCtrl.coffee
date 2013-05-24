window.WebApp.controller('ChannelCtrl', ['$scope', 'cookies', 'ContentService', '$location', ($scope, cookies, ContentService, $location) ->


  # TODO: Load channels based on get variable (catid) currently being set but not read

  $scope.categories = ContentService.getCategories()

  $scope.menu = {
    main: 0,
    sub: 0
  }

  $scope.channels = ContentService.getChannel()

  $scope.header = (id) ->
    $scope.menu.main = id
    $scope.menu.sub = 0
    $location.search("catid=#{id}")
    $scope.channels = ContentService.getChannel(id)

  $scope.subheader = (id) ->
    $scope.channels = ContentService.getChannel(id)
    $scope.menu.sub = id
    $location.search("catid=#{id}")

])
