angular.module('WebApp').factory('OAuth', ($http, apiUrl, Services) ->

  headers = {"authorization": 'basic b3JvY2tncVJTY1NsV0tqc2ZWdXhyUTo=', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

  OAuth = {}
  ServiceUrls = Services
    # TOOD: Implement Facebook registration/login
  OAuth = {

    login: (username, password) ->
      ServiceUrls.then( (data)-> 
        $http({
          method: 'POST',
          data: $.param({username: username, password: password, grant_type: 'password'}),
          url: data.login,
          headers: headers
        })
        .then(((data) ->
          return data.data
        ),
        (data) ->
          console.log data
        )
      )

    ###
    Registers a new User
    No user validation - Implemented on the form itself.

    expects a UserParms Object:
    {
      "username": "theamazingspiderman",
      "password": "venom",
      "first_name": "Peter",
      "last_name": "Parker",
      "date_of_birth": "2003-01-24",
      "locale": "en-us",
      "email": "spidey@theavengers.com"
    }  
    ###

    register: (userParms) ->
      ServiceUrls.then( (data)-> 
        $http({
          method: 'POST',
          data: $.param(userParms),
          url: data.register,
          headers: headers
        })
        .then(((data) ->
          return data.data
        ),
        (data) ->
          return data.data
        )
      )
    refreshToken: (refreshToken) ->
      $http({
        method: 'POST',
        data: $.param({refresh_token: refreshToken, grant_type: 'refresh_token'}),
        url: apiUrl + 'ws/token/',
        headers: headers
      })
      .then(((data) ->
        return data.data
      ),
      (data) ->
        console.log data
      )

    # Accepts Username or Password (supplied as username)
    resetPassword: (username) ->
      $http({
        method: 'POST',
        data: $.param({username: username, grant_type: 'refresh_token'}),
        url: apiUrl + 'ws/reset-password/',
        headers: headers
      })
      .then(((data) ->
        if data.status == 204
          return {"status": 'success'}
        else
          return {"error": "invalid_request"}
      ),
      (data) ->
        console.log data
      )
 
    # facebook: (external_token) ->
  }

  return OAuth
)