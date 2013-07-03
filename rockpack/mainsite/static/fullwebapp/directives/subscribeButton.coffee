angular.module('WebApp').directive('subscribeButton', ['UserManager', '$route', (UserManager, $route) ->
  return {
    restrict: 'A'
    templateUrl: 'subscribeButton.html'
    controller: ($scope) ->
      if UserManager.isLoggedIn

        # Is it your channel
        if $route.current.params.userid == UserManager.oauth.credentials.user_id
          $scope.state = 'edit'
        else
          $scope.currentChannel = _.find(UserManager.recentActivity.subscribed, (channel) -> return channel == $route.current.params.channelid)
          if $scope.currentChannel?
            $scope.state = 'unsubscribe'
          else
            $scope.state = 'subscribe'
      else
        $scope.state = 'loggedout'


      $scope.subscribe = () ->
        if $scope.state == 'subscribe'
          UserManager.Subscribe($scope.channel.resource_url)
            .success(()->
              UserManager.recentActivity.subscribed.push($scope.channel.id)
              if $scope.state == 'subscribe'
                $scope.state = 'unsubscribe'
              else
                $scope.state = 'subscribe'
            )
        else
          UserManager.Unsubscribe($scope.currentChannel.subscription_resource_url)
            .success(()->
              if $scope.state == 'subscribe'
                $scope.state = 'unsubscribe'
              else
                $scope.state = 'subscribe'
            )
    link: (scope, elem, attrs) ->
      return
  }
])