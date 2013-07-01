window.WebApp.factory('UserManager', ['cookies', '$http', '$q', '$location','apiUrl', (cookies, $http, $q, $location, apiUrl) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  User = {
    credentials: {
      refresh_token: cookies.get('refresh_token'),
      user_id: cookies.get('user_id'),
      access_token: cookies.get('access_token'),
    }

    isLoggedIn: false

    timeOfLastRefresh: null

    feed: {
      etags: []
      items: []
      position: 0
      total: null
    }

    refreshToken: () ->
      $http({
        method: 'POST',
        data: $.param({refresh_token: User.credentials.refresh_token, grant_type: 'refresh_token'}),
        url: apiUrl.refresh_token,
        headers: headers
      })
      .success((data) =>
          @isLoggedIn = true
          cookies.set("access_token", data.access_token, data.expires)
          @credentials = data

          # Trigger next refresh
          @TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)
          @timeOfLastRefresh = (new Date()).getTime()
      )
      .error((data) =>
        console.log data
      )

    Login: (username, password) ->
      $http({
        method: 'POST',
        data: $.param({username: username, password: password, grant_type: 'password'}),
        url: apiUrl.login,
        headers: headers
      })
      .success((data) =>
        User._ApplyLogin(data)
        User.FetchUserData()
      )
      .error((data) =>
        console.log data
      )

    _ApplyLogin: (data) ->
      console.log 'set cookies'
      cookies.set("access_token", data.access_token, data.expires)
      cookies.set("refresh_token", data.refresh_token, 2678400)
      cookies.set("user_id", data.user_id, 2678400)
      @isLoggedIn = true
      @credentials = data
      @TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)


    ExternalLogin: (provider, external_token) ->
      $http({
        method: 'POST',
        data: $.param({'external_system': provider, 'external_token': external_token}),
        url: apiUrl.login_register_external,
        headers: headers
      })
      .success((data) ->
        User._ApplyLogin(data)
        User.TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)
      )
      .error((data)->
        console.log data
      )


    FetchUserData: () ->
      $http({
        method: 'GET',
        url: User.credentials.resource_url,
        headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
      .success((data) ->
        User.details = data
        User.FetchSubscriptions()
      )
      .error((data) =>
        console.log data
      )

    FetchActivity: () ->
      $http({
      method: 'GET',
      url: User.details.activity.resource_url,
      headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
        .success((data) ->
          console.log data
        )
        .error((data) =>
          console.log data
        )

    FetchRecentSubscriptions: (start, size) ->
      $http({
      method: 'GET',
      url: User.details.subscriptions.updates,
      params: {start: start, size: size}
      headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
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

    FetchSubscriptions: () ->
      $http({
      method: 'GET',
      url: User.details.subscriptions.resource_url,
      headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
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
        headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/json"}
        data: '"' + channelResource + '"'
      })
        .success((data) ->

        )
        .error((data) =>
          console.log data
        )

    Unsubscribe: (channelResource) ->
      $http({
        method: 'DELETE',
        url: channelResource,
        headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/json"}
      })
        .success((data) ->

        )
        .error((data) =>
          console.log data
        )

#    addVideo: (videoID) ->
#      $http({
#        method: 'POST',
#        data: [["youtube", videoID]],
#        url: "#{resourceUrl}videos/",
#        headers: {"authorization": "Bearer #{bearerToken}", "Content-Type": "application/json; charset=UTF-8"},
#      })
#        .then(((data) ->
#        return data.data
#        ),
#        (data) ->
#        return data
#        )


    logOut: () ->
      cookies.set('access_token', '')
      cookies.set('refresh_token', '')
      cookies.set('user_id', '')
      User.details = {}
      User.credentials = {}
      feed: {
        etags: []
        items: []
        position: 0
        total: null
      }
      User.isLoggedIn = false

#    getTimeToNextRefresh: () ->
#      if @timeOfLastRefresh?
#        return @credentials.expiers_in*0.9*1000 - ( (new Date()).getTime() - @timeOfLastRefresh )
#      else
#        return null

    TriggerRefresh: (timeToRefresh, token) ->
      window.setTimeout((() => @refreshToken(token)) ,timeToRefresh)

  }

])