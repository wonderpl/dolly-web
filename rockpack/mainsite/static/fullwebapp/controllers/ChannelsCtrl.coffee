window.WebApp.controller('ChannelsCtrl', ['$scope', 'cookies', 'ContentService', '$location', ($scope, cookies, ContentService, $location) ->


  # TODO: Load channels based on get variable (catid) currently being set but not read

  $scope.menu = {
    main: 0,
    sub: 0
  }

  $scope.load_channels = () ->
    if $scope.totalChannels > $scope.pagination || $scope.pagination  == 0
      ContentService.getChannels($scope.pagination, 100, $location.search().catid)
        .then((data)->
          if $scope.pagination == 0
            $scope.channels = data.items
            $scope.totalChannels = data.total
          else
            $scope.channels = $scope.channels.concat(data.items)
          $scope.pagination += 100
        )

  $scope.pagination = 0
  $scope.totalChannels = 0

  $scope.$watch((()-> return $location.search().catid), (newValue, oldValue) ->
    if newValue != oldValue
      $scope.pagination = 0
      $scope.load_channels()
  )

  $scope.categories = ContentService.getCategories()

  $scope.header = (id) ->
    $location.search("catid=#{id}")
    $scope.menu.main = id
    $scope.menu.sub = 0

  $scope.subheader = (id) ->
    $scope.menu.sub = id
    $location.search("catid=#{id}")

])
