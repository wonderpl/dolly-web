window.WebApp.controller('ChannelsCtrl', ['$scope', 'cookies', 'categoryService', 'channelsService', '$location', ($scope, cookies, categoryService, channelsService, $location) ->

  $scope.menu = {
    main: '',
    sub: ''
  }

  $scope.pagination = 0
  $scope.totalChannels = 0


  # Select menu categories based on ?catid
  $scope.categories = categoryService.fetchCategories()
  .then((data) ->
    foundCategory = false
    _.each(data, ((category) ->
      if foundCategory
        return
      else
        if category.id == $location.search().catid
          $scope.menu.category.id = category.id
          return
      _.each(category.sub_categories, ((subcategory) ->
        if subcategory.id ==  $location.search().catid
          $scope.menu = {
            main: category.id
            sub: subcategory.id
          }
      ))
    ))
  )

  $scope.load_channels = () ->
    if $scope.totalChannels > $scope.pagination || $scope.pagination  == 0
      channelsService.fetchChannels($scope.pagination, 100, $location.search().catid)
      .then( (data) ->
        if $scope.pagination == 0
          $scope.channels = data.channels.items
          $scope.totalChannels = data.channels.total
        else
          $scope.channels = $scope.channels.concat(data.channels.items)
        console.log $scope.pagination
        $scope.pagination += 100
      )


  $scope.$watch((()-> return $location.search().catid), (newValue, oldValue) ->
    if newValue != oldValue
      $scope.pagination = 0
      $scope.load_channels()
  )

  $scope.header = (id) ->
    $location.search("catid=#{id}")
    $scope.menu.main = id
    $scope.menu.sub = 0

  $scope.subheader = (id) ->
    $scope.menu.sub = id
    $location.search("catid=#{id}")

])
