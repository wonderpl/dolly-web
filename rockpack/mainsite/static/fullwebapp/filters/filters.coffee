angular.module('WebApp').filter('truncate', ($http, locale, apiUrl) ->
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
