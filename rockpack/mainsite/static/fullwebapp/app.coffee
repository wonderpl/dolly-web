window.WebApp = angular.module('WebApp', [])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/login', {templateUrl: 'login.html'})
    $routeProvider.when('/feed', {templateUrl: 'feed.html', resolve: {User: "loginService"}})
    $routeProvider.when('/profile', {templateUrl: 'profile.html'})
    $routeProvider.when('/channels', {templateUrl: 'channels.html'})
  ])
  .value('locale', window.navigator.userLanguage || window.navigator.language)