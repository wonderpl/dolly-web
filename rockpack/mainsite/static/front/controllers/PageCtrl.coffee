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
  $scope.itunesLink = window.itunesLink
  $scope.injectorUrl = window.injectorUrl

  $scope.playVideo = () ->

    if $(window).width() > 1200
      width = 1200
    else
      if $(window).width() < 1200 and $(window).width() > 960
        width = 960
      else
        width = 725

    $scope.player = new YT.Player('video', {
      videoId: 'lBFBbm1Nudc',
      width: width,
      videoId: 'lBFBbm1Nudc',
      playerVars: {
        autoplay: 1,
        showinfo: 0,
        modestbranding: 0,
        controls: 1,
        rel: 0
      }
    })

  $scope.playMobileVideo = () ->
    $(".watchvideo").removeClass('watchvideo');
    $scope.player = new YT.Player('mobilevideo', {
      videoId: 'lBFBbm1Nudc',
      width: $(window).width()
      height: $(window).width()*9/16
      playerVars: {
        showinfo: 0,
        modestbranding: 0,
        controls: 1,
        rel: 0
      }
    })

])
