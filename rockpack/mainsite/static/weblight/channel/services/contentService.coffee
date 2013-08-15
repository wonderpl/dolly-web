angular.module('Weblight').factory('ContentService', ($http, locale, apiUrl, UserManager) ->

  baseApiUrl = apiUrl.cover_art.substr(0,apiUrl.cover_art.search('/ws/')+4)

  Content = {

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

    getCoverArt: (position) ->

      $http({
        method: 'GET',
        params: {start: position}
        url: apiUrl.cover_art,
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