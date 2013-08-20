window.WebApp.controller('HeaderCtrl', ['$scope', 'cookies', '$location', 'UserManager', 'SearchService', '$rootScope', ($scope, cookies, $location, UserManager, SearchService, $rootScope) ->

  $scope.user = UserManager

  $scope.$watch('user.isLoggedIn', (newValue, oldValue) ->
    $scope.isLoggedIn = newValue
  )

  $scope.userMenu = false

  $scope.searchresults = (searchPhrase) ->
    SearchService.suggest(searchPhrase)

  # Needed to use window.location isntead of $location.path as I could not pass a get variable on redirect
  $scope.fetchresults = () ->
    window.location.assign("#/search?search=#{$scope.searchPhrase}")

  $scope.logout = ->
    $scope.user.LogOut()
    $location.path("/logout").replace()
    $rootScope.asideOpen = false

])
