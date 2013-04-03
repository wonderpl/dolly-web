'use strict';

angular.module('channelServices', ['ngResource'])

  .constant('api_urls', window.api_urls)
  .constant('channel_id', window.channel_data.id)
  ## Api url list is currently partial and not being used

  .factory('Videos', ['$http', 'api_urls', 'channel_id', ($http, api_urls, channel_id) ->
    return {
      get: (channelid, size, start, locale) -> 
        parms = "#{channelid}/?size=#{size}&start=#{start}&locale=#{locale}"
        return $http.get( 'http://lb.demo.rockpack.com/ws/abcd/channels/' + parms ).then( (data) ->
          return data.data.videos.items
        )
    }
  ])