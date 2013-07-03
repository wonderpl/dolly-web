window.WebApp.factory('activityService', ['$http', ($http) ->

  activityService = {

    fetchRecentActivity: (resourceUrl, accessToken) ->
      $http({
        method: 'GET',
        url: resourceUrl,
        headers: {"authorization": "Bearer #{accessToken}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .success((data, status, headers, config) ->
          data.cacheTime = parseInt(headers()['cache-control'].substring(headers()['cache-control'].indexOf('max-age=') + 8, headers()['cache-control'].length), 10)
          return data
        )
        .error((data) ->
          console.log data
        )
  }

  return activityService

])