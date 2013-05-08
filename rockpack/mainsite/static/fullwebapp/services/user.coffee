# The Bearer token is fetched from the rootScope
# TODO: Finish image (cover/avater) upload process, waiting for API update

angular.module('WebApp').factory('User', ($http, apiUrl, $rootScope) ->

  User = {
    getUser: (userID) ->
      $http({
        method: 'GET',
        url: apiUrl + "ws/#{userID}/",
        headers: {"authorization": "Bearer #{$rootScope.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}    
      })
      .then(((data) ->
        return data.data
      ),
      (data) ->
        console.log data
      )

    ###
    # Upadte Profile
    # Aloow change of a single property (options avilable in possibleKeys bellow)
    ###    
    updateProfile: (userID, key, value) -> 
      possibleKeys = ['username', 'password', 'first_name', 'last_name', 'date_of_birth', 'locale', 'email', 'gender']

      if $.inArray(key, possibleKeys) != -1 && typeof value != "undefined"
        $http({
          method: 'PUT',
          url: apiUrl + "ws/#{userID}/#{key}/",
          headers: {"authorization": "Bearer #{$rootScope.access_token}", "Content-Type": "application/json"},
          data: JSON.stringify(value)
        })
        .then(((data) ->
          return data.data
        ),
        (data) ->
          console.log data
        )
      else
        return {status: 'error'}

  }

  return User
)