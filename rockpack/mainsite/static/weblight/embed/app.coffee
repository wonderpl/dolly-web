window.Weblight = angular.module('Weblight', ['infinite-scroll'])
  
  .constant('channelData', window.channel_data)

  .config(['$routeProvider', '$interpolateProvider' ,'$compileProvider', ($routeProvider, $interpolateProvider, $compileProvider) ->

    $interpolateProvider.startSymbol('((');
    $interpolateProvider.endSymbol('))');

    $compileProvider.urlSanitizationWhitelist(/^\s*(https?|ftp|mailto|javascript):/)
  ])

  .filter('truncate', ->
    return (text, length, end) ->
      if (isNaN(length))
          length = 10

      if (end == undefined)
          end = "..."

      if typeof text != "undefined" 
        if (text.length <= length || text.length - end.length <= length)
            return text
        else
            return String(text).substring(0, length-end.length) + end
  )

   .filter('minutes', ->
    return (text, end) ->

      if typeof text != "undefined"
        seconds = text%60
        if text%60 < 10
          seconds = "0#{text%60}"
        return "#{Math.floor(text/60)}:#{seconds}"
  )

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
      return
    )
  return
