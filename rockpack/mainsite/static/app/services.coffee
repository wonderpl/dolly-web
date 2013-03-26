'use strict';

angular.module('channelServices', ['ngResource'])

  .constant('api_urls', window.api_urls)
  .constant('channel_id', window.channel_data.id)
  ## Api url list is currently partial and not being used

  .factory('Videos', ['$resource', 'api_urls', 'channel_id', ($resource, api_urls, channel_id) ->
    $resource('http://lb.demo.rockpack.com/ws/abcd/channels/'+channel_id, {
      get: {method:'GET', params:{locale: '', size: 40}}
    })
  ])