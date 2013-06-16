window.contentApp.controller('PageCtrl', ['isMobile', '$scope', '$location', 'browserServices', (isMobile, $scope, $location, browserServices) ->

  $scope.triggerEvent = (action, label) ->
    ga('send', 'event', 'uiAction', action, label)

  $scope.browser = browserServices

  $scope.toggle = (e, hiddenelement) ->
    $(e.currentTarget).toggleClass('activestate').siblings('.bio').toggleClass('activestate')

  $scope.toggleReadMore = (e, hiddenelement) ->
    $(e.currentTarget).toggleClass('activestate').siblings('.'+hiddenelement).toggleClass('activestate')
    if $(e.currentTarget).hasClass('activestate')
      $(e.currentTarget).siblings(".readmoretext").show("fast")
      $(e.currentTarget).children(".btntext").html('Read Less')
    else
      $(e.currentTarget).siblings(".readmoretext").hide("fast")
      $(e.currentTarget).children(".btntext").html('Read More')


  $scope.assets_url = window.assets_url
  $scope.injectorUrl = window.injectorUrl

  $scope.playVideo = () ->
    $scope.player = new YT.Player('video', {
      videoId: 'lBFBbm1Nudc',
      playerVars: {
        autoplay: 1,
        showinfo: 1,
        modestbranding: 1,
        wmode: "opaque",
        controls: 1
      }
    })

  $scope.playMobileVideo = () ->
    $scope.player = new YT.Player('mobilevideo', {
      height: 450,
      width: $(window).width(),
      videoId: 'lBFBbm1Nudc',
      playerVars: {
        autoplay: 1,
        showinfo: 1,
        modestbranding: 1,
        wmode: "opaque",
        controls: 1
      }
    })

])
