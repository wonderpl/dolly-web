window.WebApp.controller('HeaderCtrl', ['$scope', 'cookies', '$location', 'UserManager', 'SearchService', '$rootScope', ($scope, cookies, $location, UserManager, SearchService, $rootScope) ->

  $scope.user = UserManager

  $scope.showSearch = false

  $scope.$watch('user.isLoggedIn', (newValue, oldValue) ->
    $scope.isLoggedIn = newValue
  )

  $scope.$watch((()-> $location.path()), (newValue) ->
    if newValue.indexOf('/channel/') > 0
      $scope.isTransparent = true
    else
      $scope.isTransparent = false
  )

  $scope.userMenu = false

  $scope.searchresults = (typedSearch) ->
    SearchService.suggest(typedSearch)

  # Needed to use window.location isntead of $location.path as I could not pass a get variable on redirect
  $scope.fetchresults = () ->
    console.log searchform
    window.location.assign("#!/search?search=#{$scope.searchPhrase}")

  $scope.logout = ->
    $scope.user.LogOut()
    $location.path("/logout").replace()
    $rootScope.asideOpen = false

])
