window.Bookmarklet.controller('LoginCtrl', ['$scope','$http', '$location', 'cookies', 'OAuth', '$rootScope', ($scope, $http, $location, cookies, OAuth, $rootScope) ->

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
        $rootScope.refresh_token = data.refresh_token
        $rootScope.user_id = data.user_id
        ga('send', 'event', 'bookmarklet', 'login', 'rockpack')
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
            cookies.set('refresh_token', data.data.refresh_token, 2678400)
            cookies.set('user_id', data.data.user_id, 2678400)
            $rootScope.refresh_token = data.refresh_token
            $rootScope.user_id = data.user_id
            ga('send', 'event', 'bookmarklet', 'login', 'facebook')
            $location.path('/addtochannel')
            return
          )
      else
        # cancelled
    )
  $scope.close = ->
    window.parent.postMessage('close', '*');

  return
])

window.Bookmarklet.controller('AddtoChannelCtrl', ['$scope','$http', '$location', 'cookies', 'OAuth', 'User', '$routeParams', '$rootScope', ($scope, $http, $location, cookies, OAuth, User, $routeParams, $rootScope) ->

  $scope.videoID = $routeParams.id
  $scope.selectedChannel = null

  $scope.refresh_token = cookies.get('refresh_token') or $rootScope.refresh_token
  $scope.user_id = cookies.get('user_id') or $rootScope.user_id

  # redirect user to login if he got here by chance
  if ($scope.refresh_token == null or $scope.user_id == null)
    $location.path('/')

  # Access token is alway refreshed.
  $scope.refreshToken = OAuth.refreshToken($scope.refresh_token)
  .then((data)->
    $scope.access_token = data.access_token
    cookies.set('access_token', data.access_token, 3600)
    $scope.User = User.getUser($scope.access_token, data.resource_url)
    return
  )

  $scope.isSelected = (resource_url) ->
    return $scope.selectedChannel == resource_url

  $scope.selectChannel = (channelResource) ->
    $scope.selectedChannel = channelResource
    return

  $scope.addtoChannel = () ->
    if $scope.selectedChannel != null
      User.addVideo($scope.access_token, $scope.videoID,$scope.selectedChannel)
      .then((data) ->
        if data.status == 400
          alert ('Unable to add video, please try again')
        else
          $location.path('/done')
      )

  $scope.createChannel = ->
    $location.path('/createchannel')

  $scope.close = ->
    window.parent.postMessage('close', '*');
  
  return
])

window.Bookmarklet.controller('CreateChannelCtrl', ['$scope','$http', '$location', 'cookies', 'OAuth', 'User', '$routeParams', ($scope, $http, $location, cookies, OAuth, User, $routeParams) ->
  $scope.accessToken = cookies.get('access_token')
  $scope.user_id = cookies.get('user_id')

  $scope.close = ->
    window.parent.postMessage('close', '*');

  $scope.addChannel = ->
    User.createChannel( $scope.accessToken, $scope.channelName)
    .then((data) ->
        User.addVideo($scope.access_token, $routeParams.id, data.resource_url)
          .then((data) ->
            $location.path('/done')
          )
    )
  return

])

window.Bookmarklet.controller('DoneCtrl', ['$scope','$http', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, $location, cookies, OAuth, User) ->
  $scope.close = ->
    window.parent.postMessage('close', '*');

  ga('send', 'event', 'bookmarklet', 'channelUpdated')

])

window.Bookmarklet.controller('ResetPasswordCtrl', ['$scope','$http', '$location', 'cookies', 'OAuth', 'User', ($scope, $http, $location, cookies, OAuth, User) ->

  $scope.message = {}

  $scope.close = ->
    window.parent.postMessage('close', '*');

  $scope.resetPassword = ->
    $scope.error = ''
    OAuth.resetPassword($scope.username)
    .success((data) ->
        $scope.response = {message: "Check your email and follow the instructions", success: true}
      )
    .error((data)->
        $scope.response = {message: "Sorry we did not recognise this username or email", success: false}
    )

])