window.contentApp.factory('browserServices', () ->

  @searchString = (data) ->
    for i in data
      dataString = i.string
      dataProp = i.prop
      @versionSearchString = i.versionSearch || i.identity
      if (dataString)
        if (dataString.indexOf(i.subString) != -1)
          return i.identity
      else if (dataProp)
        return i.identity

  @searchVersion = (dataString) ->
    index = dataString.indexOf(@versionSearchString)
    if (index == -1) then return
    return parseFloat(dataString.substring(index+@versionSearchString.length+1))

  @dataBrowser = [
    {
      string: navigator.userAgent,
      subString: "Chrome",
      identity: "Chrome"
    },
    {
      string: navigator.userAgent,
      subString: "OmniWeb",
      versionSearch: "OmniWeb/",
      identity: "OmniWeb"
    },
    {
      string: navigator.vendor,
      subString: "Apple",
      identity: "Safari",
      versionSearch: "Version"
    },
    {
      prop: window.opera,
      identity: "Opera",
      versionSearch: "Version"
    },
    {
      string: navigator.vendor,
      subString: "iCab",
      identity: "iCab"
    },
    {
      string: navigator.vendor,
      subString: "KDE",
      identity: "Konqueror"
    },
    {
      string: navigator.userAgent,
      subString: "Firefox",
      identity: "Firefox"
    },
    {
      string: navigator.vendor,
      subString: "Camino",
      identity: "Camino"
    },
    {		# for newer Netscapes (6+)
      string: navigator.userAgent,
      subString: "Netscape",
      identity: "Netscape"
    },
    {
      string: navigator.userAgent,
      subString: "MSIE",
      identity: "Explorer",
      versionSearch: "MSIE"
    },
    {
      string: navigator.userAgent,
      subString: "Gecko",
      identity: "Mozilla",
      versionSearch: "rv"
    },
    { 		# for older Netscapes (4-)
      string: navigator.userAgent,
      subString: "Mozilla",
      identity: "Netscape",
      versionSearch: "Mozilla"
    }
  ]

  @dataOS = [
    {
      string: navigator.platform,
      subString: "Win",
      identity: "Windows"
    },
    {
      string: navigator.platform,
      subString: "Mac",
      identity: "Mac"
    },
    {
      string: navigator.userAgent,
      subString: "iPhone",
      identity: "iPhone/iPod"
    },
    {
      string: navigator.platform,
      subString: "Linux",
      identity: "Linux"
    }
  ]

  @browser = @searchString(this.dataBrowser) || "An unknown browser";
  @version = @searchVersion(navigator.userAgent) or @searchVersion(navigator.appVersion) or "an unknown version";
  @OS = @searchString(this.dataOS) || "an unknown OS";

  return {browser: @browser, version: @version, os: @OS}
)