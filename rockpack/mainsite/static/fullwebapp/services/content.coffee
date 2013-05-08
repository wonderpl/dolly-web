angular.module('WebApp').factory('Content', ($http, locale) ->

  Content = {

    getCovers: (start, size) ->
      if typeof start == "undefined"
        start = 0
      if typeof size == "undefined"
        size = 20

      $http({
        method: 'GET',
        url: apiUrl + 'ws/cover_art/',
        data: $.param({'start': start, 'size': size, 'locale' : locale}),
      })
      .then(((data) ->
        return data.data.cover_art
      ),
      (data) ->
        console.log data
      )

    getCategories: ->
      $http({
        method: 'GET',
        url: apiUrl + 'ws/videos/'
        data: $.param({'start': start, 'size': size, 'locale': locale})
      })
      .then(((data) ->
        return data.data.categories
      ),
      (data) ->
        console.log data
      )

    getVideos: (category, start, size) ->
      if typeof start == "undefined"
        start = 0
      if typeof size == "undefined"
        size = 20

      dataObj = {'start': start, 'size': size}

      if typeof category != undefined
        dataObj.category = category

      dataObj.locale = locale

      $http({
        method: 'GET',
        url: apiUrl + 'ws/videos/',
        data: $.param(dataObj)
      })
      .then(((data) ->
        console.log data.data.videos
        return data.data.videos
      ),
      (data) ->
        console.log data
      )

  }

  return Content
)