window.contentApp.factory('GATrackingService', ($route) ->

  return {
    push: () ->
      return ga('send', 'pageview', $route.current.$route.templateUrl);
  }
)