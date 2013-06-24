angular.module('channelServices', ['ngResource'])

  # Api url list is currently partial and not being used

  .factory('Videos', ['$http', ($http) ->
    return {
      get: (size, start, locale) ->
        parms = "?size=#{size}&start=#{start}&locale=#{locale}&_callback=JSON_CALLBACK"
        return $http.jsonp( channel_data.resource_url + parms).then( (data) ->
          return data.data.videos.items
        )
    }
  ])
