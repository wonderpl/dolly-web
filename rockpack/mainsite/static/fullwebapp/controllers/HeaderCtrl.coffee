window.WebApp.controller('HeaderCtrl', ['$scope', 'cookies', '$location', 'UserManager', 'SearchService', ($scope, cookies, $location, UserManager, SearchService) ->

  $scope.user = UserManager

  $scope.$watch('user.oauth.isLoggedIn', (newValue, oldValue) ->
    console.log newValue
    $scope.isLoggedIn = newValue
  )

  $scope.userMenu = false

  $scope.searchresults = (searchPhrase) ->
    SearchService.suggest(searchPhrase)

  # Needed to use window.location isntead of $location.path as I could not pass a get variable on redirect
  $scope.fetchresults = () ->
    window.location.assign("#/search?search=#{$scope.searchPhrase}")

  console.log $scope.user

  $scope.logout = ->
    $scope.user.logOut()
    $location.path("/login").replace()

])
