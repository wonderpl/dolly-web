window.WebApp = angular.module('WebApp', [])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/login', {templateUrl: 'login.html'})
    $routeProvider.when('/feed', {templateUrl: 'feed.html', controller: 'FeedCtrl', resolve: {userObj: "RequireLoginService"}})
    $routeProvider.when('/profile', {templateUrl: 'profile.html', controller: 'ProfileCtrl', resolve: {userObj: "RequireLoginService"}})
    $routeProvider.when('/channels', {templateUrl: 'channels.html', controller: 'ChannelCtrl', resolve: {userObj: "RequireLoginService"}})
  ])
  .value('locale', window.navigator.userLanguage || window.navigator.language)