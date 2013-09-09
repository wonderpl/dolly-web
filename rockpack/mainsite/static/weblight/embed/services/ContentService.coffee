window.Weblight.factory('ContentService', ($http) ->

  Content = {

    getChannelVideos: (size, start) ->

      dataObj = {'start': start, 'size': size}
      url = window.channel_data.resource_url
      headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

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