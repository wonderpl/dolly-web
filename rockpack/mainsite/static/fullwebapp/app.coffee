window.WebApp = angular.module('WebApp', ['infinite-scroll','ui.bootstrap'])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/login', {templateUrl: 'login.html'})
    $routeProvider.when('/search', {templateUrl: 'search.html', reloadOnSearch: false})
    $routeProvider.when('/:userid/channel', {templateUrl: 'editchannel.html', reloadOnSearch: false})
    $routeProvider.when('/:userid/channel/:channelid', {templateUrl: 'channel.html', reloadOnSearch: false})
    $routeProvider.when('/reset-password', {templateUrl: 'resetPassword.html'})
    $routeProvider.when('/register', {templateUrl: 'register.html'})
    $routeProvider.when('/feed', {
      templateUrl: 'feed.html',
      controller: 'FeedCtrl',
      reloadOnSearch: false
    })
    $routeProvider.when('/:userid/profile', {
      templateUrl: 'profile.html',
      controller: 'ProfileCtrl',
    })
    $routeProvider.when('/channels', {
      templateUrl: 'channels.html',
      controller: 'ChannelsCtrl',
      reloadOnSearch: false
    })
  ])
  .value('locale', window.navigator.userLanguage || window.navigator.language)
  .constant('apiUrl', window.apiUrls)
window.onYouTubeIframeAPIReady = ->
  updateScope()
  return

updateScope = ->
  injector = angular.element(document.getElementById('WebApp')).injector()
  if typeof injector == "undefined"
    setTimeout(updateScope, 300)
  else
    injector.invoke(($rootScope, $compile, $document) ->
      $rootScope.playerReady = true
      $rootScope.$apply()
    )
  return