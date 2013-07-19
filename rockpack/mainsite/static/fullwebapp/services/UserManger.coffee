# TODO: Disable timers on log out
# TODO: still room for refactoring

window.WebApp.factory('UserManager', ['cookies', '$http', '$q', '$location','apiUrl', 'activityService', 'oauthService', (cookies, $http, $q, $location, apiUrl, activityService, oauthService) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}


  User = {

    feed:
      items: []
      total: null
      position: 0

    activity: activityService
    oauth: oauthService

    recentActivity: {
      cacheTime: 0
      recently_starred: []
      recently_viewed: []
      subscribed: []
    }

    logOut: () ->
      cookies.set('access_token', '')
      cookies.set('refresh_token', '')
      cookies.set('user_id', '')
      User.details = {}
      User.oauth.credentials = {}
      feed: {
        items: []
        position: 0
        total: null
      }
      User.oauth.isLoggedIn = false
      console.log 'finished logging out'

    recentActivityTimedRetrive: () ->
      activityService.fetchRecentActivity(User.details.activity.resource_url, User.oauth.credentials.access_token)
        .success((data) ->
          User.recentActivity.recently_starred = _.union(User.recentActivity.recently_starred, data.recently_starred)
          User.recentActivity.recently_viewed = _.union(User.recentActivity.recently_viewed, data.recently_viewed)
          User.recentActivity.subscribed = _.union(User.recentActivity.subscribed, data.subscribed)
          User.recentActivity.cacheTime = data.cacheTime
          setTimeout((
            () ->
              User.recentActivityTimedRetrive()
          ), User.recentActivity.cacheTime*1000)
        )

    FetchUserData: () ->
      deferred = $q.defer()
      $http({
        method: 'GET',
        url: User.oauth.credentials.resource_url,
        headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
      .success((data) ->
        User.details = data
        User.FetchUnreadNotifications()
        User.FetchNotifications()
        User.recentActivityTimedRetrive()
        .success((data) ->
            deferred.resolve(data)
        )

      )
      .error((data) =>
        console.log data
        deferred.reject ('failed to retreive data')
      )

      return deferred.promise

    FetchRecentSubscriptions: (start, size) ->
      $http({
      method: 'GET',
      url: User.details.subscriptions.updates,
      params: {start: start, size: size}
      headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .success((data, status, headers, config) ->

          if User.feed.total == null
            User.feed.total = data.videos.total

          currentPos = 0

          _.each(data.videos.items, (video) ->
            datestring  = video.date_added.substr(0, 10)

            while User.feed.items[currentPos]? and  User.feed.items[currentPos].date != datestring
              currentPos++

            if not (User.feed.items[currentPos]?)
              User.feed.items[currentPos] = {date: datestring, videos: []}

            User.feed.items[currentPos].videos.push(video)
          )
        )
        .error((data) =>
          console.log data
        )

    Report: (object_type, object_id) ->
      $http({
        method: 'POST',
        url: "#{apiUrl.oauth.credentials.resource_url}content_reports/"
        headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        data: {object_type: object_type, object_id: object_id}
      })
        .then(((data) ->

        ), (data) ->
          console.log data
        )


    FetchNotifications: () ->
      $http({
      method: 'GET',
      url: User.details.notifications.resource_url,
      headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .then(((data) ->
          User.details.notifications.total = data.data.notifications.total
          User.details.notifications.items = data.data.notifications.items
        ), (data) ->
          console.log data
        )

    #TODO: Add resource url for unread notifications
    FetchUnreadNotifications: () ->
      $http({
        method: 'GET',
        url: "#{User.details.notifications.resource_url}unread_count/",
        headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .success((data) ->
          if data != 0 and parseInt(data) != User.details.notifications.unread_count
            User.details.notifications.unread_count = parseInt(data)
            User.FetchNotifications()
        )
        .error((data) =>
          console.log data
        )


    FetchSubscriptions: () ->
      $http({
      method: 'GET',
      url: User.details.subscriptions.resource_url,
      headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .success((data) ->
          User.details.subscriptions.subscribedChannels = data.channels
        )
        .error((data) =>
          console.log data
        )

    Subscribe: (channelResource) ->
      $http({
        method: 'POST',
        url: User.details.subscriptions.resource_url,
        headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/json"}
        data: '"' + channelResource + '"'
      })
        .success((data) ->

        )
        .error((data) =>
          console.log data
        )

    Unsubscribe: (channelID) ->
      $http({
        method: 'DELETE',
        url: "#{User.oauth.credentials.resource_url}subscriptions/#{channelID}/",
        headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/json"}
      })
        .success((data) ->

        )
        .error((data) =>
          console.log data
        )

#    CreateChannel: () ->
#      $http({
#        method: 'POST',
#        url: User.details.channels.resource_url,
#        headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/json"}
#        data: '"' + channelResource + '"'
#      })
#        .success((data) ->
#
#        )
#        .error((data) =>
#          console.log data
#        )
    addVideo: (channelurl, videoId) ->
      $http({
        method: 'POST',
        data: [videoId],
        url: "#{channelurl}videos/",
        headers: {"authorization": "Bearer #{User.oauth.credentials.access_token}", "Content-Type": "application/json"}
      })
        .success((data) ->
          return data.data
        )
        .error((data) ->
          return data
        )

#    getTimeToNextRefresh: () ->
#      if @timeOfLastRefresh?
#        return @credentials.expiers_in*0.9*1000 - ( (new Date()).getTime() - @timeOfLastRefresh )
#      else
#        return null


  }


  return User
])