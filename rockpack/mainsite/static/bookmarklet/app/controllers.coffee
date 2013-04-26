window.Bookmarklet.controller('LoginCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', ($scope, $http, apiUrl, $location, cookies, OAuth) ->

  @refresh_token = cookies.get('refresh_token')
  @user_id = cookies.get('user_id')

  ## TODO - check that a videoid was supplied or give an error
  if (@refresh_token != null and @user_id != null)
    $location.path('/addtochannel')

  $scope.submit = ->  
    if typeof $scope.username != "undefined" and typeof $scope.password != "undefined"
      OAuth.login($scope.username, $scope.password)
      .then((data) ->
        # Saving Access Token for 1 Hour
        # Cookies.set('access_token', data.access_token, 3600)
        # Saving refresh Token for 1 Month
        cookies.set('refresh_token', data.refresh_token, 2678400)
        cookies.set('user_id', data.user_id, 2678400)
        $location.path('/addtochannel')
        return
      )
      .error((data) ->
        ## TODO give an error message
        console.log data
        return
      )
    return

  $scope.facebook = ->
    FB.getLoginStatus((response) ->
      if (response.status == 'connected')
        console.log response
        OAuth.externalLogin('facebook', response.authResponse.accessToken)
          .then((data) ->
            console.log data
            return
          )
      else
        # Not Logged in/User refused access
        FB.login((response) ->
          if (response.authResponse)
            # connected
            OAuth.externalLogin('facebook', response.authResponse.accessToken)
              .then((data) ->
                console.log data
                return
              )
          else
            # cancelled
            console.log response
        )
    )


  $scope.close = ->
    parent.removeIframe()

  return
])

window.Bookmarklet.controller('AddtoChannelCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, apiUrl, $location, cookies, OAuth, User) ->

  $scope.refresh_token = cookies.get('refresh_token')
  $scope.user_id = cookies.get('user_id')
  $scope.selectedVideo = null

  # redirect user to login if he got here by chance
  if (@refresh_token == null or @user_id == null)
    $location.path('/')

  # Access token is alway refreshed.
  $scope.refreshToken = OAuth.refreshToken($scope.refresh_token)
  .then((data)->
    $scope.access_token = data.access_token
    cookies.set('access_token', data.access_token, 3600)
    $scope.User = User.getUser($scope.user_id, $scope.access_token)
    return
  )

  $scope.selectChannel = (el) ->
    if $scope.selectedVideo == $(el.currentTarget).data("channelid")
      $scope.selectedVideo = null
      $(el.currentTarget).removeClass("selected")
    else
      $scope.selectedVideo = $(el.currentTarget).data("channelid")
      $(".selected").each(->
        $(this).removeClass('selected')
      )
      $(el.currentTarget).addClass("selected")
    return

  $scope.createChannel = ->
    $location.path('/createchannel')

  $scope.close = ->
    parent.removeIframe()
  return
])

window.Bookmarklet.controller('CreateChannelCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, apiUrl, $location, cookies, OAuth, User) ->
  $scope.accessToken = cookies.get('access_token')
  $scope.user_id = cookies.get('user_id')

  $scope.close = ->
    parent.removeIframe()

  $scope.addChannel = ->
    User.createChannel($scope.user_id, $scope.accessToken, $scope.channelName)
  return

])
