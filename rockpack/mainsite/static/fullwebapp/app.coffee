window.WebApp = angular.module('WebApp', ['infinite-scroll','ui.bootstrap'])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/login', {templateUrl: 'login.html'})
    $routeProvider.when('/search', {templateUrl: 'search.html'})
    $routeProvider.when('/channel/:userid/:channelid', {templateUrl: 'channel.html'})
    $routeProvider.when('/feed', {
      templateUrl: 'feed.html',
      controller: 'FeedCtrl',
      resolve: {
        userObj: (RequireLoginService) ->
          return RequireLoginService.checkLogin().then((response) ->
            return response
          )
      }
    })
    $routeProvider.when('/profile', {
      templateUrl: 'profile.html',
      controller: 'ProfileCtrl',
      resolve: {
        userObj: (RequireLoginService) ->
          return RequireLoginService.checkLogin().then((response) ->
            return response
          )
      }
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
  injector = angular.element(document.getElementById('app')).injector()
  if typeof injector == "undefined"
    setTimeout(updateScope, 300)
  else
    injector.invoke(($rootScope, $compile, $document) ->
      $rootScope.playerReady = true
      $rootScope.$apply()
    )
  return