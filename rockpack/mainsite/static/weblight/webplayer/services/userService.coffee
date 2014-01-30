angular.module('WebLite').factory('userService', ($http) ->

  User = {
    fetchUser: (userID) ->
      $http({
        method: 'GET',
        url: "#{window.apiUrls.base_api}#{userID}/",
      })
      .then((data) ->
        return data.data
      )
  }

  return User
)