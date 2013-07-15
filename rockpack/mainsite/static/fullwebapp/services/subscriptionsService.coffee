angular.module('WebApp').factory('subscriptionsService', ($http, locale, apiUrl, UserManager) ->

  Subscriptions = {
    FetchSubscriptions: (userID) ->
      $http({
        method: 'GET',
        url: User.details.subscriptions.resource_url,
      })
      .success((data) ->
        User.details.subscriptions.subscribedChannels = data.channels
      )
      .error((data) =>
        console.log data
      )
  }

  return Subscriptions

)