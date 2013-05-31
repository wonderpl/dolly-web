angular.module('channelServices', ['ngResource'])

  # Api url list is currently partial and not being used

  .factory('Videos', ['$http', ($http) ->
    return {
      get: (size, start, locale) ->
        parms = "?size=#{size}&start=#{start}&locale=#{locale}"
        return $http.get( channel_data.resource_url + parms ).then( (data) ->
          return data.data.videos.items
        )
    }
  ])