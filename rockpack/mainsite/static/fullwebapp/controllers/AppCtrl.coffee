# TODO: Rejection reason is not captured

window.WebApp.controller('AppCtrl', ['$rootScope', '$location', ($rootScope, $location) ->
  $rootScope.$on("$routeChangeError", (current, previous, rejection) ->
    $location.path("/login").replace()
  )
])
