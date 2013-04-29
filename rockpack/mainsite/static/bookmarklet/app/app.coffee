window.Bookmarklet = angular.module('Bookmarklet', [])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/', {templateUrl: 'login.html'})
    $routeProvider.when('/addtochannel', {templateUrl: 'addtochannels.html'})
    $routeProvider.when('/createchannel', {templateUrl: 'createchannel.html'})
    $routeProvider.when('/resetpassword', {templateUrl: 'resetpassword.html'})
    $routeProvider.when('/done', {templateUrl: 'done.html'})
  ])
  .constant('apiUrl', 'http://demo.rockpack.com/')

window.fbAsyncInit = ->
  FB.init({ appId: 'Your_APP_ID',
  status: true,
  cookie: true,
  xfbml: true,
  oauth: true})

  showLoader(true)