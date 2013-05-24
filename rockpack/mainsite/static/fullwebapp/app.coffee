window.WebApp = angular.module('WebApp', ['infinite-scroll'])
  .config(['$routeProvider', ($routeProvider) ->
    $routeProvider.when('/login', {templateUrl: 'login.html'})
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
      controller: 'ChannelCtrl',
      resolve: {
        userObj: (RequireLoginService) ->
          return RequireLoginService.checkLogin().then((response) ->
            return response
          )
      },
      reloadOnSearch: false
    })
  ])
  .value('locale', window.navigator.userLanguage || window.navigator.language)
  .constant('apiUrl', window.apiUrls)