'use strict';

angular.module('channelServices', ['ngResource']).
  factory('Videos', ['$resource', ($resource) ->
    $resource('http://lb.demo.rockpack.com/ws/abcd/channels/:channelID/', {},{
      get: {method:'GET', params:{locale: '', size: 40}}
    })
  ])
