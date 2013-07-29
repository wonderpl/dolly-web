angular.module('WebApp').factory('shareService', ['$http', 'UserManager', 'apiUrl', '$rootScope', ($http, UserManager, apiUrl, $rootScope) ->

  Share = {
    fetchShareUrl: (object_type, object_id) ->
      $http({
        method: 'POST',
        url: apiUrl.share_url,
        headers: {"authorization": "Bearer #{UserManager.credentials.access_token}", "Content-Type": "application/json"}
        data: {object_type: object_type, object_id: object_id},
      })
      .success((data) ->
        $rootScope.message = {
          message: data
        }
        return data
      )

  }

  return Share
])