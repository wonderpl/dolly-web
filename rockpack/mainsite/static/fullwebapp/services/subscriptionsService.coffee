###
  Used to fetch subscriptions of unregistered users (for viewing other peoples profile)
###

angular.module('WebApp').factory('subscriptionsService', ($http, locale, apiUrl, UserManager) ->

  Subscriptions = {
    FetchSubscriptions: (userID) ->
      $http({
        method: 'GET',
        url: "#{apiUrl.base_api}#{userID}/subscriptions/",
      })
  }

  return Subscriptions

)