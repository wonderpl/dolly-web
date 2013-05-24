window.WebApp.factory('UserManager', ['cookies', '$http', '$q', '$location', (cookies, $http, $q, $location) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  User = {
    credentials: {
      refresh_token: cookies.get('refresh_token'),
      user_id: cookies.get('user_id'),
      access_token: cookies.get('access_token')
    }

    timeOfLastRefresh: null

    feed: [],

    refreshToken: () ->
      $http({
        method: 'POST',
        data: $.param({refresh_token: User.credentials.refresh_token, grant_type: 'refresh_token'}),
        url: window.apiUrls['refresh_token'],
        headers: headers
      })
      .success((data) =>
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
        url: window.apiUrls['login'],
        headers: headers
      })
      .success((data) =>
        @TriggerRefresh(data.expires_in*0.9*1000, data.refresh_token)
        @credentials = data
        console.log 'login'
        cookies.set("access_token", data.access_token, data.expires)
        cookies.set("refresh_token", data.refresh_token, 2678400)
        cookies.set("user_id", data.user_id, 2678400)
      )
      .error((data) =>
        console.log data
      )

    FetchUserData: (resourceUrl) ->
      $http({
        method: 'GET',
        url: resourceUrl,
        headers: {"authorization": "Bearer #{@credentials.access_token}", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
      })
      .success((data) ->
        User.details = data
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
        .success((data) ->
          currentPos = 0
          _.each(data.videos.items, (video) ->
            datestring  = video.date_added.substr(0, 10)

            while User.feed[currentPos]? and  User.feed[currentPos].date != datestring
              currentPos++

            if not (User.feed[currentPos]?)
              User.feed[currentPos] = {date: datestring, videos: []}

            User.feed[currentPos].videos.push(video)
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

    logOut: () ->
      cookies.set('access_token', '')
      cookies.set('refresh_token', '')
      cookies.set('user_id', '')
      User.details = {}
      User.credentials = {}


  getTimeToNextRefresh: () ->
      if @timeOfLastRefresh?
        return @credentials.expiers_in*0.9*1000 - ( (new Date()).getTime() - @timeOfLastRefresh )
      else
        return null

    TriggerRefresh: (timeToRefresh, token) ->
      window.setTimeout((() => @refreshToken(token)) ,timeToRefresh)

  }

])