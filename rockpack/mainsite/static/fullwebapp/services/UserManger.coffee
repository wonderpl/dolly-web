# TODO: Disable timers on log out
# TODO: still room for refactoring

window.WebApp.factory('UserManager', ['cookies', '$http', '$q', '$location','apiUrl', 'activityService', 'oauthService', (cookies, $http, $q, $location, apiUrl, activityService, oauthService) ->

  ApplyLogin = (data) ->
    cookies.set("access_token", data.access_token, data.expires)
    cookies.set("refresh_token", data.refresh_token, 2678400)
    cookies.set("user_id", data.user_id, 2678400)
    User.isLoggedIn = true
    User.credentials = data
    User.TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)

  User = {

    feed: {
      items: []
      total: null
      position: 0
    }

    recentActivity: {
      cacheTime: 0
      recently_starred: []
      recently_viewed: []
      subscribed: []
    }

    isLoggedIn: false

    credentials: {
      refresh_token: cookies.get('refresh_token'),
      user_id: cookies.get('user_id'),
      access_token: cookies.get('access_token'),
    }


    TriggerRefresh: (timeToRefresh, token) ->
      window.setTimeout((() -> User.RefreshToken(token)) ,timeToRefresh)

    LogOut: () ->
      cookies.set('access_token', '')
      cookies.set('refresh_token', '')
      cookies.set('user_id', '')
      User.details = {}
      User.credentials = {}
      feed: {
        items: []
        position: 0
        total: null
      }
      User.isLoggedIn = false

    LogIn: (username, password) ->
      oauthService.LogIn(username, password)
        .then((data) ->
          ApplyLogin(data)
          return data.data

        )

    Register: (user) ->
      oauthService.Register(user)
        .then((data) ->
          ApplyLogin(data)
          return data.data
        )

    ExternalLogin: (provider, external_token) ->
      oauthService.ExternalLogin(provider, external_token)
        .then((data) ->
          ApplyLogin(data.data)
          User.FetchUserData()
          .then((data) ->
              $location.path('/channels')
              return data.data
          )
          return data.data
        )


#   Automatically refresh the token after 90% of the token refresh time has expired
    RefreshToken: () ->
      oauthService.RefreshToken(User.credentials.refresh_token)
        .then((data) ->
          User.isLoggedIn = true
          cookies.set("access_token", data.access_token, data.expires)
          User.credentials = data.data

          # Trigger next refresh
          User.TriggerRefresh(data.data.expires_in*0.9*1000, data.refresh_token)
          User.timeOfLastRefresh = (new Date()).getTime()
        )

    FetchUserData: (resource_url) ->
      $http({
        method: 'GET',
        url: User.credentials.resource_url,
        headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
      .then((data) ->
        _.each(data.data.channels.items, (channel) ->
          channel.cover.thumbnail_url = channel.cover.thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
        )
        User.details = data.data

#       DISABLED Notification + Activity fetching as mostly relevant for full web

#        User.FetchUnreadNotifications()
#        User.FetchNotifications()
#        User.RecentActivityTimedRetrive()
        )

    Report: (object_id, object_type) ->
      $http({
        method: 'POST',
        url: "#{User.credentials.resource_url}content_reports/"
        headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        data: $.param({object_type: "#{object_type}", object_id: "#{object_id}", reason: "Web Reoprt"})
      })


    FetchSubscriptions: () ->
      $http({
      method: 'GET',
      url: User.details.subscriptions.resource_url,
      headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
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
        headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/json"}
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
        url: "#{User.credentials.resource_url}subscriptions/#{channelID}/",
        headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/json"}
      })
        .success((data) ->

        )
        .error((data) =>
          console.log data
        )

    addVideo: (channelurl, videoId) ->
      $http({
        method: 'POST',
        data: [videoId],
        url: "#{channelurl}videos/",
        headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/json"}
      })
        .success((data) ->
          return data.data
        )
        .error((data) ->
          return data
        )

 #   Notifications are part of Full web, NOT IN USE
    FetchNotifications: () ->
      $http({
      method: 'GET',
      url: User.details.notifications.resource_url,
      headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .then(((data) ->
          User.details.notifications.total = data.data.notifications.total
          User.details.notifications.items = data.data.notifications.items
        ), (data) ->
          console.log data
        )

#   Notifications are part of Full web, NOT IN USE
    FetchUnreadNotifications: () ->
      $http({
        method: 'GET',
        url: "#{User.details.notifications.resource_url}unread_count/",
        headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .success((data) ->
          if data != 0 and parseInt(data) != User.details.notifications.unread_count
            User.details.notifications.unread_count = parseInt(data)
            User.FetchNotifications()
        )
        .error((data) =>
          console.log data
        )

#   Used by the old Feed system (full web) NOT IN USE
    FetchRecentSubscriptions: (start, size) ->
      $http({
      method: 'GET',
      url: User.details.subscriptions.updates,
      params: {start: start, size: size}
      headers: {"authorization": "Bearer #{User.credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
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
#
#    getTimeToNextRefresh: () ->
#      if @timeOfLastRefresh?
#        return @credentials.expiers_in*0.9*1000 - ( (new Date()).getTime() - @timeOfLastRefresh )
#      else
#        return null


  }


  return User
])