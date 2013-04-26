window.Bookmarklet = angular.module('Bookmarklet', [])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/', {templateUrl: 'login.html'})
    $routeProvider.when('/addtochannel', {templateUrl: 'addtochannels.html'})
    $routeProvider.when('/createchannel', {templateUrl: 'createchannel.html'})
    $routeProvider.when('/resetpassword', {templateUrl: 'resetpassword.html'})

  ])
  .constant('apiUrl', 'http://localhost:5000/')

window.fbAsyncInit = ->
  FB.init({ appId: 'Your_APP_ID',
  status: true,
  cookie: true,
  xfbml: true,
  oauth: true})

  showLoader(true)

