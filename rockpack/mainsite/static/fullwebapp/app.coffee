window.WebApp = angular.module('WebApp', [])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/login', {templateUrl: 'login.html'})
    $routeProvider.when('/feed', {templateUrl: 'feed.html', controller: 'FeedCtrl', resolve: {userObj: "UserManager"}})
    $routeProvider.when('/profile', {templateUrl: 'profile.html', controller: 'ProfileCtrl', resolve: {userObj: "UserManager"}})
    $routeProvider.when('/channels', {templateUrl: 'channels.html', controller: 'ChannelCtrl', resolve: {userObj: "UserManager"}})
  ])
  .value('locale', window.navigator.userLanguage || window.navigator.language)