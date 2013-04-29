window.Bookmarklet.controller('LoginCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', ($scope, $http, apiUrl, $location, cookies, OAuth) ->

  @refresh_token = cookies.get('refresh_token')
  @user_id = cookies.get('user_id')

  ## TODO - check that a videoid was supplied or give an error
  if (@refresh_token != null and @user_id != null)
    $location.path('/addtochannel')

  $scope.submit = ->  
    if typeof $scope.username != "undefined" and typeof $scope.password != "undefined"
      OAuth.login($scope.username, $scope.password)
      .then(((data) ->
        # Saving refresh Token for 1 Month
        cookies.set('refresh_token', data.refresh_token, 2678400)
        cookies.set('user_id', data.user_id, 2678400)
        console.log 'went ok'
        $location.path('/addtochannel')
        return
      ),
      (data) ->
          alert ('Bad username/password')
          return
      )

  $scope.facebook = ->
    FB.login((response) ->
      if (response.authResponse)
        # connected
        OAuth.externalLogin('facebook', response.authResponse.accessToken)
          .then((data) ->
            cookies.set('refresh_token', data.refresh_token, 2678400)
            cookies.set('user_id', data.user_id, 2678400)
            $location.path('/addtochannel')
            return
          )
      else
        # cancelled
        console.log response
    )
  $scope.close = ->
    window.parent.postMessage('close', '*');

  return
])

window.Bookmarklet.controller('AddtoChannelCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', 'User', '$routeParams', ($scope, $http, apiUrl, $location, cookies, OAuth, User, $routeParams) ->

  $scope.videoID = $routeParams.id
  $scope.selectedChannel = null

  $scope.refresh_token = cookies.get('refresh_token')
  $scope.user_id = cookies.get('user_id')

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

  $scope.isSelected = (channelID) ->
    return $scope.selectedChannel == channelID

  $scope.selectChannel = (channelID) ->
    $scope.selectedChannel = channelID
    return

  $scope.addtoChannel = () ->
    User.addVideo($scope.user_id, $scope.access_token, $scope.videoID,$scope.selectedChannel)
    .then((data) ->
      $location.path('/done')
    )

  $scope.createChannel = ->
    $location.path('/createchannel')

  $scope.close = ->
    window.parent.postMessage('close', '*');
  
  return
])

window.Bookmarklet.controller('CreateChannelCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, apiUrl, $location, cookies, OAuth, User) ->
  $scope.accessToken = cookies.get('access_token')
  $scope.user_id = cookies.get('user_id')

  $scope.close = ->
    parent.removeIframe()

  $scope.addChannel = ->
    User.createChannel($scope.user_id, $scope.accessToken, $scope.channelName)
    .then((data) ->
      $location.path('/done')
    )
  return

])

window.Bookmarklet.controller('DoneCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, apiUrl, $location, cookies, OAuth, User) ->
  $scope.close = ->
    window.parent.postMessage('close', '*');

])

window.Bookmarklet.controller('ResetPasswordCtrl', ['$scope','$http', 'apiUrl', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, apiUrl, $location, cookies, OAuth, User) ->
  $scope.close = ->
    window.parent.postMessage('close', '*');

  $scope.resetPassword = ->
    OAuth.resetPassword($scope.username)

])