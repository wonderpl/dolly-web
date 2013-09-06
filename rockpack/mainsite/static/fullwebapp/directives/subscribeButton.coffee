#TODO: UserManager is not being passed properly/watched, won't change to unsubscribe!
angular.module('WebApp').directive('subscribeButton', ['UserManager', '$route', (UserManager, $route) ->
  return {
    restrict: 'A'
    templateUrl: 'subscribeButton.html'
    replace: true
    controller: ($scope) ->
      if UserManager.isLoggedIn
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
              $scope.state = 'unsubscribe'
            )
        else
          UserManager.Unsubscribe($scope.channel.id)
            .success(()->
              UserManager.recentActivity.subscribed.splice(UserManager.recentActivity.subscribed.indexOf($scope.channel.id), 1)
              $scope.state = 'subscribe'
            )
    link: (scope, elem, attrs) ->
      return
  }
])