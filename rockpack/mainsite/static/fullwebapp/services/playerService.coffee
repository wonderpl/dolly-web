window.WebApp.factory('playerService', [() ->

  currentChannel = null
  currentVideo = null
  currentVideoPosition = null
  # 0 - hidden, 1 - visible on main stage, 2 - visible on aside
  playerLocation = 0

  playerService = {
    setNewPlaylist: (channel, videoid, location) ->
      # Stop Playing Video, Clear playlist, restart new playlist starting with the selected video
      if currentChannel != channel
        currentChannel = channel
        # We need to update the channel list as well
      currentVideo = _.find(currentChannel.videos.items, (videoObj) -> videoObj.id == videoid)
      currentVideoPosition = currentChannel.videos.items.indexOf(currentVideo)
      playerLocation = location

    playVideoFromChannel: (positionId) ->
      if positionId > currentChannel.videos.total
        positionId = 0
      else if positionId  < 0
          positionId = currentChannel.videos.total-1

      currentVideo = currentChannel.videos.items[positionId]
      currentVideoPosition = positionId

    getVideo: () ->
      return currentVideo

    getVideoPosition: () ->
      return currentVideoPosition

    getChannel: () ->
      return currentChannel

    closePlayer: () ->
      currentChannel = null
      currentVideo = null
      playerLocation = 0

    setLocation: (location) ->
      playerLocation = location

    getLocation: ()->
      return playerLocation
  }

  return playerService

])