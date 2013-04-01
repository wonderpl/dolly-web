window.Weblight.controller('PageCtrl', ['$routeParams', 'isMobile', '$scope', ($routeParams, isMobile, $scope) -> 
  $("body").css({"background-image": "url(/static/images/blueheader.png)", "background-repeat": "repeat-x", "background-color": "#f1f1f1"})

  $scope.toggle = (e, hiddenelement) -> 
    $(e.currentTarget).toggleClass('activestate').siblings('.'+hiddenelement).toggleClass('activestate')
])
