
(function() {
  
  var checkMatch, i, iframes, importVideos, inject, l, typeMap;
  
  importVideos = function(args) {
    var a, qs;
    qs = [];
    a = void 0;
    for (a in args) {
      if (args.hasOwnProperty(a)) {
        qs.push(a + "=" + args[a]);
      }
    }
    inject(qs.join("&"));
    return true;
  };
  
  checkMatch = function(re, str) {
    var match;
    match = re.exec(str || window.location);
    if (match) {
      return importVideos({
        source: match[1],
        type: typeMap[match[2]] || match[2],
        id: match[3]
      });
    }
  };

  inject = function(video) {
    var css, newIframe;
    css = document.createElement("link");
    css.href = "http://demo.rockpack.com/static/bookmarklet/bookmarklet/style.css";
    css.type = "text/css";
    css.rel = "stylesheet";
    document.getElementsByTagName("head")[0].appendChild(css);
    newIframe = document.createElement('iframe');
    newIframe.src = 'http://demo.rockpack.com/bookmarklet#/?' + video;
    newIframe.id = 'rockpackiframe';
    newIframe.name = "rockpackiframe";
    newIframe.setAttribute('allowtransparency', 'true');
    newIframe.style.display = "none";
    document.body.appendChild(newIframe);

    document.getElementById("movie_player").setAttribute('wmode','transparent');

    var newdiv = document.createElement("div");
    newdiv.id = "rockpackdiv";
    document.getElementById("player-api").appendChild(newdiv);

    document.getElementById('rockpackdiv').appendChild(document.getElementById('movie_player'));


    if (!window.addEventListener) {
      window.attachEvent("message", receiveMessage);
    }
    else {
      window.addEventListener('message', receiveMessage, false);
    }
    

    function receiveMessage(evt)
    {
      var element;
      element = document.getElementById("rockpackiframe");
      element.parentNode.removeChild(element);
      window.removeEventListener('message', receiveMessage, false);
    }

    document.getElementById("rockpackiframe").onload = function() {
      document.getElementById("rockpackiframe").style.display = "block";
    };
  };

  
  typeMap = {
    v: "video",
    embed: "video",
    list: "playlist"
  };

  iframes = void 0;
  i = void 0;
  l = void 0;
  if (checkMatch(/(youtube)\.com\S*(v)=([\w\-]{11})/)) {
    return;
  }
  if (checkMatch(/(youtube)\.com\/(user)\/(\w+)/)) {
    return;
  }
  if (checkMatch(/(youtube)\.com\S*(list)=([\w\-]+)/)) {
    return;
  }
  iframes = document.getElementsByTagName("iframe");
  i = 0;
  l = iframes.length;
  while (i < l) {
    if (checkMatch(/(youtube)\.com\/(embed)\/([\w\-]{11})/, iframes[i].src)) {
      return;
    }
    i++;
  }
  return window.alert("No video found");
})();
