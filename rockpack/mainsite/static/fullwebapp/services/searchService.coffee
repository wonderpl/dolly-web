angular.module('WebApp').factory('SearchService', ($http, locale, apiUrl, $q) ->

  Content = {
    suggest: (phrase) ->
      console.log apiUrl
      dfr = $q.defer()
      $http({
      method: 'GET',
      url: apiUrl.video_search_terms,
      params: {'q': phrase},
      })
      .then((data) ->
        searchResults = JSON.parse(data.data.slice(19, data.data.length-1))
        resultArray = []
        _.each(searchResults[1], (result) ->
          resultArray.push(result[0])
        )
        dfr.resolve(resultArray)
      )
      return dfr.promise

    channelSearch: (phrase, start, size) ->
      $http({
        method: 'GET',
        url: apiUrl.channel_search,
        params: {'q': phrase, start: start, size: size},
      })
      .then((data) ->
        return data.data
      )

    videoSearch: (phrase, start, size) ->
      $http({
        method: 'GET',
        url: apiUrl.video_search,
        params: {'q': phrase, start: start, size: size},
      })
      .then((data) ->
        return data.data
      )

    userSearch: (phrase, start, size) ->
      $http({
        method: 'GET',
        url: apiUrl.user_search,
        params: {'q': phrase, start: start, size: size},
      })
      .then((data) ->
        return data.data
      )
  }
  return Content
)