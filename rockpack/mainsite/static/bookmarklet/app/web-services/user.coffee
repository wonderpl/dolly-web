angular.module('Bookmarklet').factory('User', ($http) ->

  user_model = {}

  User = {
    getUser: (bearerToken, resource_url) ->
      $http({
        method: 'GET',
        url: resource_url,
        headers: {"authorization": "Bearer #{bearerToken}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
      .then(((data) ->
        user_model = data.data
        return data.data
      ),
      (data) ->
        console.log data
      )

    createChannel: (bearerToken, channelName) ->
      $http({
      method: 'POST',
      data: $.param({title: channelName, description: '', category: '', cover: '', public: false}),
      url: user_model.channels.resource_url,
      headers: {"authorization": "Bearer #{bearerToken}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
      })
        .then(((data) ->
          return data.data
        ),
        (data) ->
          console.log data
          return data.data
        )

    addVideo: (bearerToken, videoID, resourceUrl) ->
      $http({
      method: 'POST',
      data: [["youtube", videoID]],
      url: "#{resourceUrl}videos/",
      headers: {"authorization": "Bearer #{bearerToken}", "Content-Type": "application/json; charset=UTF-8"},
      })
        .then(((data) ->
          console.log data
          return data.data
        ),
        (data) ->
          console.log data
        )
  }

  return User
)