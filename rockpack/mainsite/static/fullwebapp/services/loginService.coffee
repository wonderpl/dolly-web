window.WebApp.factory('loginService', ['$rootScope', 'OAuth', '$location', 'cookies', '$q', ($rootScope, OAuth, $location, cookies, $q) ->

  defer = $q.defer()
  @refresh_token = cookies.get('refresh_token')
  @user_id = cookies.get('user_id')

  # No user cradentials, redirect to login
  if (@refresh_token == null or @user_id == null)
    defer.reject("error")


  return defer.promise
])