angular.module('WebLite').factory('ContentService', ($http) ->

  Content = {

    getChannelVideos: (channelID, size, start) ->

      dataObj = {'start': start, 'size': size}
      url = "#{apiUrls.base_api}-/channels/#{channelID}/"
      headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

      $http({
        method: 'GET',
        url: url,
        params: dataObj,
        headers: headers,
      })
        .then(((data) ->
          return data
        ),
        (data) ->
          console.log data
        )

  }

  return Content
)