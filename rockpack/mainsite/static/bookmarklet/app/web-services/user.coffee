angular.module('Bookmarklet').factory('User', ($http, apiUrl) ->

  User = {
    getUser: (userID, bearerToken) ->
      $http({
        method: 'GET',
        url: apiUrl + "ws/#{userID}/",
        headers: {"authorization": "Bearer #{bearerToken}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}    
      })
      .then(((data) ->
        return data.data
      ),
      (data) ->
        console.log data
      )

    createChannel: (userID, bearerToken, channelName) ->
      $http({
      method: 'POST',
      data: $.param({title: channelName, description: '', category: '', cover: '', public: false}),
      url: apiUrl + "ws/#{userID}/channels/",
      headers: {"authorization": "Bearer #{bearerToken}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
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