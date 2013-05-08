window.WebApp = angular.module('WebApp', [])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/', {templateUrl: 'login.html'})
    $routeProvider.when('/feed', {templateUrl: 'feed.html'})
    $routeProvider.when('/profile', {templateUrl: 'profile.html'})
    $routeProvider.when('/channels', {templateUrl: 'channels.html'})
  ])
  .value('locale', window.navigator.userLanguage || window.navigator.language)
