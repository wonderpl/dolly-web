angular.module('WebApp').filter('truncate', ($http, locale, apiUrl) ->
  return (text, length, end) ->
    if (isNaN(length))
      length = 30

    if (end == undefined)
      end = "..."

    if typeof text != "undefined"
      if text.length+3 <= length
        return text
      else
        return String(text).substring(0, length-end.length-3) + end
)

angular.module('WebApp').filter('weekDay', ($http, locale, apiUrl) ->
  return (text, length, end) ->

    # if we can't parse this into a date just return text as it is
    Today = new Date()
    feedDate = new Date(text)

    Weekdays = [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednsday',
      'Thursday',
      'Friday',
      'Saturday'
    ]

    diff = Today.getDate() - Today.getDay() + (Today.getDay()== 0 ? -6:1)
    startofWeek = new Date(Today.setDate(diff))

    if feedDate > startofWeek
      return Weekdays[feedDate.getDay()]
    else
      return text
)
