#jslint sloppy:true plusplus:true

#global window,document
(->
  importVideos = (args) ->
    qs = ["locale={{ request.args.locale }}"]
    a = undefined
    for a of args
      qs.push a + "=" + args[a]  if args.hasOwnProperty(a)
#    window.location.assign "{{ url_for('.index', _external=True) }}?" + qs.join("&")
    inject(qs.join("&"))
    true

  checkMatch = (re, str) ->
    match = re.exec(str or window.location)
    if match
      importVideos
        source: match[1]
        type: typeMap[match[2]] or match[2]
        id: match[3]

  inject = (video) ->
    css = document.createElement("link");
    css.href = "http://127.0.0.1:9001/bookmarklet/style.css";
    css.type = "text/css";
    css.rel = "stylesheet";
    document.getElementsByTagName("head")[0].appendChild(css);

    newIframe = document.createElement('iframe')
    newIframe.src = 'http://127.0.0.1:9001/?' + video
    newIframe.id = 'rockpackiframe'
    newIframe.name="rockpackiframe"
    newIframe.setAttribute('allowtransparency', 'true')
    newIframe.style.display = "none";
    document.body.appendChild(newIframe)
    frames["rockpackiframe"].onload = ->
      document.getElementById("rockpackiframe").style.display = "block";

  window.removeIframe = () ->
    element = document.getElementById("rockpackiframe")
    element.parentNode.removeChild(element)


  typeMap =
    v: "video"
    embed: "video"
    list: "playlist"

  iframes = undefined
  i = undefined
  l = undefined

  # Check if page url refers to youtube video:
  return  if checkMatch(/(youtube)\.com\S*(v)=([\w\-]{11})/)

  # Check if page url refers to youtube user/channel:
  return  if checkMatch(/(youtube)\.com\/(user)\/(\w+)/)

  # Check if page url refers to youtube playlist:
  return  if checkMatch(/(youtube)\.com\S*(list)=([\w\-]+)/)

  # Else check the page for embedded video player:
  iframes = document.getElementsByTagName("iframe")
  i = 0
  l = iframes.length

  while i < l
    return  if checkMatch(/(youtube)\.com\/(embed)\/([\w\-]{11})/, iframes[i].src)
    i++
  window.alert "No video found"
)()