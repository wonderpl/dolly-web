window.Bookmarklet = angular.module('Bookmarklet', [])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/', {templateUrl: 'login.html'})
    $routeProvider.when('/addtochannel', {templateUrl: 'addtochannels.html'})
    $routeProvider.when('/createchannel', {templateUrl: 'createchannel.html'})
    $routeProvider.when('/resetpassword', {templateUrl: 'resetpassword.html'})
    $routeProvider.when('/done', {templateUrl: 'done.html'})

  ])
  .value('api_urls', window.api_urls)

ga('send', 'event', 'bookmarklet', 'opened')
