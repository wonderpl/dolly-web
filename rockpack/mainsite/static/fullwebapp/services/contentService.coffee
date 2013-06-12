angular.module('WebApp').factory('ContentService', ($http, locale, apiUrl) ->

  compareDecending = (a, b) ->
    a = a.priority
    b = b.priority

    if (a != b)
      if (a < b || typeof a == 'undefined')
        return 1
      if (a > b || typeof b == 'undefined')
        return -1
    return 1

  Content = {

    getCovers: (start, size) ->
      if typeof start == "undefined"
        start = 0
      if typeof size == "undefined"
        size = 20

      $http({
        method: 'GET',
        url: apiUrl.cover_art,
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
        url: apiUrl.categories,
      })
      .then(((data) ->


        #
        data.data.categories.items.sort(compareDecending)
        _.each(data.data.categories.items, (category) ->
          tempcategory = []
          _.each(category.sub_categories, (subcategory) ->
            if subcategory.priority > 0
              tempcategory.push(subcategory)
          )
          category.sub_categories = tempcategory
          category.sub_categories.sort(compareDecending)

        )
        return data.data.categories.items
      ),
      (data) ->
        console.log data
      )

    getChannels: (start, size, categoryID) ->
      if typeof start == "undefined"
        start = 0
      if typeof size == "undefined"
        size = 20

      dataObj = {'start': start, 'size': size}

      if typeof categoryID != "undefined"
        dataObj.category = categoryID

      $http({
      method: 'GET',
      url: apiUrl.popular_channels,
      params: dataObj,
      })
        .then(((data) ->
          return data.data.channels
        ),
        (data) ->
          console.log data
        )

    #TODO: Implement call, currently copy/paste
    getChannelVideos: (categoryID, start, size) ->
      if typeof start == "undefined"
        start = 0
      if typeof size == "undefined"
        size = 20

      dataObj = {'start': start, 'size': size}

      if typeof categoryID != "undefined"
        dataObj.category = categoryID

      $http({
        method: 'GET',
        url: apiUrl.popular_channels,
        params: dataObj,
      })
        .then(((data) ->
        return data.data.channels
        ),
        (data) ->
          console.log data
        )

  }

  return Content
)