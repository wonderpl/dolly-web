###
  Used for the Channels Page. Fetches a list of channels based on the categoryID
###

# TODO: implement Etag check

angular.module('WebApp').factory('channelsService', ($http, locale, apiUrl, UserManager) ->

  Categories = {
    categoryID: null
    items: []
    etags: []

    fetchChannels: (start, size, categoryID) ->
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
        _.each(data.data.channels.items, (channel)->
          channel.cover.thumbnail_url = channel.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
        )
        return data.data
      ),
        (data) ->
          console.log data
      )
  }

  return Categories

)