angular.module('WebApp').factory('loggedoutUserService', (apiUrl, $rootScope, $http) ->

  User = {
    fetchUser: (userID) ->
      $http({
        method: 'GET',
        url: "#{apiUrl.base_api}#{userID}/",
      })
      .then((data) ->
        return data.data
      )
  }

  return User
)