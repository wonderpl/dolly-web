window.WebApp.factory('videoShareService', [() ->

  videoObj = {}
  isVisible = false

  videoService = {
    getVideoObj: () ->
      return videoObj

    setVideoObj: (vo) ->
      videoObj = vo

    isVisible: () ->
      return isVisible

    setVisibility: (state) ->
      isVisible = state
  }

  return videoService

])