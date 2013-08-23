window.WebApp.controller('ProfileCtrl', ['$scope', 'UserManager', '$routeParams', 'subscriptionsService', 'loggedoutUserService', '$location', ($scope, UserManager, $routeParams, subscriptionsService, loggedoutUserService, $location) ->

  $scope.isMyProfile = UserManager.isLoggedIn and $routeParams.userid == UserManager.credentials.user_id

  $scope.getState = () ->
    return $routeParams.state

  $scope.$watch($scope.getState, (newValue, oldValue) ->
    if newValue in ['channels', 'subscriptions']
      $scope.state = newValue
    else
      $scope.state = 'channels'
  )

  $scope.changeState = (state) ->
      $location.search('state', state)

  if $scope.isMyProfile
    $scope.channels = UserManager.details.channels.items
    $scope.User = UserManager
    $scope.User.largeAvatar = $scope.User.details.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
    UserManager.FetchSubscriptions()
      .success((data) ->
        $scope.subscriptions = UserManager.details.subscriptions.subscribedChannels
      )
  else

    subscriptionsService.FetchSubscriptions($routeParams.userid)
      .then((data) ->
        $scope.subscriptions = data.data.channels
      )

    loggedoutUserService.fetchUser($routeParams.userid)
      .then((data) ->
        $scope.User = {
          credentials: {
            user_id: $routeParams.userid
          }
          details: data
        }
        $scope.User.largeAvatar = data.avatar_thumbnail_url.replace('thumbnail_medium', 'thumbnail_large')
      )
])
