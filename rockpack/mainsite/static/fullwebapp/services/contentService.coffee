angular.module('WebApp').factory('ContentService', ($http, locale, apiUrl, UserManager) ->

  baseApiUrl = apiUrl.cover_art.substr(0,apiUrl.cover_art.search('/ws/')+4)

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

#    getCovers: (start, size) ->
#      if typeof start == "undefined"
#        start = 0
#      if typeof size == "undefined"
#        size = 20
#
#      $http({
#        method: 'GET',
#        url: apiUrl.cover_art,
#        data: $.param({'start': start, 'size': size, 'locale' : locale}),
#      })
#      .then(((data) ->
#        return data.data.cover_art
#      ),
#      (data) ->
#        console.log data
#      )

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
      .success((data) ->
        _.each(data.channels.items, (channel)->
          channel.cover.thumbnail_url = channel.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
        )
        return data
      )
      .error((data) ->
        console.log data
      )

    #TODO: Check if this is your channel, if so move to https and attach cradentials
    getChannelVideos: (userID, categoryID, size, start) ->

      dataObj = {'start': start, 'size': size}
      url = "#{baseApiUrl}#{userID}/channels/#{categoryID}/"
      headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

      if UserManager.credentials.user_id == userID
        headers = {"authorization": "Bearer #{UserManager.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
#        url = "#{baseApiUrl}#{userID}/channels/#{categoryID}".replace("http://", "https://secure.")

      $http({
        method: 'GET',
        url: url,
        params: dataObj,
        headers: headers,
      })
        .then(((data) ->
          return data.data
        ),
        (data) ->
          console.log data
        )

  }

  return Content
)