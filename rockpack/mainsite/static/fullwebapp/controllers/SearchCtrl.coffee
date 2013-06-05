window.WebApp.controller('SearchCtrl', ['$scope', 'SearchService', '$q', ($scope, SearchService, $q) ->

  $scope.searchresults = (searchPhrase) ->
    SearchService.suggest(searchPhrase)


  $scope.fetchresults = () ->
    $scope.videos = SearchService.videoSearch($scope.searchPhrase, 0, 50)
    $scope.channels = SearchService.channelSearch($scope.searchPhrase, 0, 50)
])
