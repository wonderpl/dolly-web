!function(){for(var e=0,t=["webkit","moz"],n=0;n<t.length&&!window.requestAnimationFrame;++n)window.requestAnimationFrame=window[t[n]+"RequestAnimationFrame"],window.cancelAnimationFrame=window[t[n]+"CancelAnimationFrame"]||window[t[n]+"CancelRequestAnimationFrame"];window.requestAnimationFrame||(window.requestAnimationFrame=function(t){var n=(new Date).getTime(),s=Math.max(0,16-(n-e)),r=window.setTimeout(function(){t(n+s)},s);return e=n+s,r}),window.cancelAnimationFrame||(window.cancelAnimationFrame=function(e){clearTimeout(e)})}(),OO.plugin("WonderUIModule",function(e){var t={elements:{},mousedown:!1,scrubbed:!1,seekTimeout:void 0,loaderTimeout:void 0},n='<div id="wonder-poster"><img src="/assets/img/trans.png" alt="" id="wonder-poster" class="blur"/><span class="f-thin f-uppercase"></span></div><a href="#" id="wonder-loader" class="show"></a><div id="wonder-controls"><a href="#" class="play wonder-play icon-play"></a><a href="#" class="pause wonder-pause icon-pause hidden"></a><a href="#" class="volume wonder-volume vol-high"></a><a href="#" class="wonder-logo"></a><a href="#" class="fullscreen wonder-fullscreen icon-fullscreen"></a><span class="wonder-timer">--:--</span><div class="scrubber vid"><div class="scrubber-progress vid"></div><a href="#" class="scrubber-handle vid icon-circle"></a></div><div class="scrubber-target vid"><img src="/assets/img/trans.png" class="scrubber-trans vid" width="100%" height="100%" /></div><div class="scrubber vol"><div class="scrubber-progress vol"></div><a href="#" class="scrubber-handle vol icon-circle"></a></div><div class="scrubber-target vol"><img src="/assets/img/trans.png" class="scrubber-trans vol" width="100%" height="100%" /></div></div>';return t.WonderUIModule=function(e,n){t.mb=e,t.id=n,t.init()},t.init=function(){t.state={playing:!1,fullscreen:!1},t.mb.subscribe(e.EVENTS.PLAYER_CREATED,"wonder",t.onPlayerCreate),t.mb.subscribe(e.EVENTS.PLAYHEAD_TIME_CHANGED,"wonder",t.onTimeUpdate),t.mb.subscribe(e.EVENTS.CONTENT_TREE_FETCHED,"wonder",t.onContentReady),t.mb.subscribe(e.EVENTS.PLAYED,"wonder",t.onPlayed),t.mb.subscribe(e.EVENTS.PAUSE,"wonder",t.onPause),t.mb.subscribe(e.EVENTS.PLAY,"wonder",t.onPlay),t.mb.subscribe(e.EVENTS.PLAYER_EMBEDDED,"wonder",t.hideLoader),window.wonderPlayer=this,window.wonder=t},t.onPlayerCreate=function(e,s){t.wrapper=document.createElement("div"),t.wrapper.setAttribute("id","wonder-wrapper"),t.wrapper.innerHTML=n,t.playerElem=document.getElementById(s),t.playerElem.parentNode.insertBefore(t.wrapper,t.playerElem),t.wrapper.insertBefore(t.playerElem,document.getElementById("wonder-poster")),t.elements.wrapper=document.getElementById("wonder-wrapper"),t.elements.controls=document.getElementById("wonder-controls"),t.elements.poster=document.getElementById("wonder-poster"),t.elements.loader=document.getElementById("wonder-loader"),t.elements.playbutton=document.querySelector(".wonder-play"),t.elements.pausebutton=document.querySelector(".wonder-pause"),t.elements.fullscreenbutton=document.querySelector(".wonder-fullscreen"),t.elements.volumebutton=document.querySelector(".wonder-volume"),t.elements.timer=document.querySelector(".wonder-timer"),t.elements.scrubbers=document.querySelectorAll(".scrubber"),t.elements.scrubber_handles=document.querySelectorAll(".scrubber-handle"),t.elements.scrubber_targets=document.querySelectorAll(".scrubber-target"),t.elements.scrubber_trans=document.querySelectorAll(".scrubber-trans"),t.elements.scrubber_progress_vid=document.querySelector(".scrubber-progress.vid"),t.elements.scrubber_handle_vid=document.querySelector(".scrubber-handle.vid"),t.elements.scrubber_progress_vol=document.querySelector(".scrubber-progress.vol"),t.elements.scrubber_handle_vol=document.querySelector(".scrubber-handle.vol"),t.listen(t.elements.playbutton,"click",t.play),t.listen(t.elements.pausebutton,"click",t.pause),t.listen(t.elements.fullscreenbutton,"click",t.fullscreen),t.listen(t.elements.volumebutton,"click",t.volume),t.listen(t.elements.loader,"click",t.togglePlay),t.isTouchDevice()?(t.addClass(t.elements.controls,"touch"),t.listen(t.elements.scrubber_trans,"touchmove",t.scrubTouch),t.listen(t.elements.scrubber_trans,"touchstart",t.scrubDown),t.listen(t.elements.scrubber_trans,"touchleave",t.scrubUp),t.listen(t.elements.scrubber_trans,"touchend",t.scrubUp)):(t.listen(t.elements.scrubber_trans,"mousemove",t.scrubMouse),t.listen(t.elements.scrubber_trans,"mousedown",t.scrubDown),t.listen(t.elements.scrubber_trans,"mouseup",t.scrubUp),t.listen(t.elements.scrubber_trans,"mouseleave",t.scrubUp))},t.onContentReady=function(e,n){t.info=n,t.elements.poster.getElementsByTagName("img")[0].src=n.promo||n.promo_image,t.elements.loader.className="",t.elements.poster.getElementsByTagName("span")[0].innerHTML=t.info.title,t.duration=n.duration},t.onTimeUpdate=function(e,n,s){t.time=n,t.duration=s,t.displayTime=t.state.playing===!1?t.getTime(t.duration):t.getTime(t.time),t.elements.timer.innerHTML=t.displayTime,t.state.playing===!0&&t.mousedown===!1?requestAnimationFrame(t.tick):cancelAnimationFrame(t.tick)},t.onPlay=function(){t.state.playing===!1&&(t.addClass(t.elements.poster,"hide"),t.addClass(t.elements.playbutton,"hidden"),t.removeClass(t.elements.pausebutton,"hidden"),t.state.playing=!0)},t.onPause=function(){t.state.playing===!0&&(t.removeClass(t.elements.playbutton,"hidden"),t.addClass(t.elements.pausebutton,"hidden"),t.hideLoader(),t.state.playing=!1)},t.onPlayed=function(){t.state.playing=!1,t.removeClass(t.elements.playbutton,"hidden"),t.addClass(t.elements.pausebutton,"hidden"),cancelAnimationFrame(t.tick),clearTimeout(t.loaderTimeout),t.hideLoader()},t.togglePlay=function(){t.state.playing===!0?t.pause():t.play()},t.play=function(n){t.prevent(n),t.mb.publish(e.EVENTS.PLAY)},t.pause=function(n){t.prevent(n),t.mb.publish(e.EVENTS.PAUSE)},t.volume=function(n){t.prevent(n),t.volume>0?t.mb.publish(e.EVENTS.CHANGE_VOLUME,0):t.mb.publish(e.EVENTS.CHANGE_VOLUME,.5)},t.rewind=function(){t.time-30>=0&&0!==t.time?t.seek(t.time-30):t.seek(0)},t.seek=function(n){t.mb.publish(e.EVENTS.SEEK,n),t.mb.publish(e.EVENTS.PLAY)},t.fullscreen=function(){t.state.fullscreen===!1?(t.mb.publish(e.EVENTS.FULLSCREEN_CHANGED),t.attemptFullscreen(t.elements.wrapper),t.addClass(t.elements.wrapper,"fullscreen"),t.state.fullscreen=!0):(document.exitFullscreen?document.exitFullscreen():document.mozExitFullScreen?document.mozExitFullScreen():document.mozCancelFullScreen?document.mozCancelFullScreen():document.webkitExitFullscreen&&document.webkitExitFullscreen(),t.removeClass(t.elements.wrapper,"fullscreen"),t.state.fullscreen=!1)},t.scrubMouse=function(e){if(t.mousedown===!0){t.prevent(e);var n,s=e.clientX,r=e.srcElement||e.target,l=r.className.replace("scrubber-trans ","");return clearTimeout(t.seekTimeout),t.seekTimeout=setTimeout(function(){n=s-r.getBoundingClientRect().left,n=n/r.clientWidth*100,"vid"===l?t.scrubVid(n):"vol"===l&&t.scrubVol(n)},10),!1}},t.scrubTouch=function(e){if(t.mousedown===!0){t.prevent(e);{var n,s=e.touches[0]||e.changedTouches[0];s.pageX}return clearTimeout(t.seekTimeout),t.seekTimeout=setTimeout(function(){n=s.pageX-t.elements.scrubber.getBoundingClientRect().left,n=n/t.elements.scrubber.clientWidth*100,n>=0&&100>=n?(t.seek(t.duration/100*n),t.elements.scrubber_progress.style.width=n+"%",t.elements.scrubber_handle.style.left=n+"%"):t.scrubUp()},10),!1}},t.scrubDown=function(e){t.prevent(e),t.mousedown=!0,t.old_time=t.time,t.addClass(t.elements.scrubber_handles,"down")},t.scrubUp=function(e){t.prevent(e),t.mousedown===!0&&(t.mousedown=!1,t.removeClass(t.elements.scrubber_handles,"down"))},t.scrubVid=function(e){t.seek(t.duration/100*e),t.elements.scrubber_progress_vid.style.width=e+"%",t.elements.scrubber_handle_vid.style.left=e+"%"},t.scrubVol=function(n){t.mb.publish(e.EVENTS.CHANGE_VOLUME,n/100),t.elements.scrubber_progress_vol.style.width=n+"%",t.elements.scrubber_handle_vol.style.left=n+"%"},t.showLoader=function(){clearTimeout(t.loaderTimeout),t.elements.loader.className="show"},t.hideLoader=function(){clearTimeout(t.loaderTimeout),t.elements.loader.className=""},t.tick=function(){var e=t.time/t.duration*100+"%";t.elements.scrubber_progress_vid.style.width=e,t.elements.scrubber_handle_vid.style.left=e,t.elements.loader.className="",clearTimeout(t.loaderTimeout),t.loaderTimeout=setTimeout(function(){t.state.playing===!0&&(t.elements.loader.className="show")},250)},t.attemptFullscreen=function(e){e.requestFullscreen?e.requestFullscreen():e.mozRequestFullScreen?e.mozRequestFullScreen():e.webkitRequestFullscreen?e.webkitRequestFullscreen():e.msRequestFullscreen&&e.msRequestFullscreen()},t.hasClass=function(e,t){return-1===e.className.indexOf(t)?!1:!0},t.addClass=function(e,n){for(var s=t.select(e),r=0;r<s.length;r++)-1===s[r].className.indexOf(n)&&(s[r].className+=(0===s[r].className.length?"":" ")+n)},t.removeClass=function(e,n){for(var s=t.select(e),r=0;r<s.length;r++)-1!==s[r].className.indexOf(n)&&(-1!==s[r].className.indexOf(n+" ")?s[r].className=s[r].className.replace(n+" ",""):-1!==s[r].className.indexOf(" "+n)?s[r].className=s[r].className.replace(" "+n,""):s[r].className.length===n.length&&(s[r].className=""))},t.extend=function(e,t){for(var n in t)e[n]=e.hasOwnProperty(n)?e[n]:t[n];return e},t.getTime=function(e){e=Number(e);var t=Math.floor(e/3600),n=Math.floor(e%3600/60),s=Math.floor(e%3600%60);return(t>0?t+":":"")+(n>0?(t>0&&10>n?"0":"")+n+":":"0:")+(10>s?"0":"")+s},t.prevent=function(e){"undefined"!=typeof e&&(e.preventDefault?e.preventDefault():e.stopPropagation?e.stopPropagation():e.returnValue=!1)},t.select=function(e){var n;if("string"==typeof e)return-1!==e.indexOf("#")?[document.getElementById(e.split("#")[1])]:-1!==e.indexOf(".")?(n=Array.prototype.slice.call(document.querySelectorAll(e)),n.length>0?n:null):(n=Array.prototype.slice.call(document.getElementsByTagName(e)),n.length>0?n:null);if(t.isNode(e)||t.isElement(e))return[e];if("object"==typeof e)try{return e.length>0?Array.prototype.slice.call(e):null}catch(s){return e}},t.listen=function(e,n,s){for(var r=t.select(e),l=0;l<r.length;l++)t.attach.call(r[l],n,s)},t.attach=function(){return window.addEventListener?function(e,t){this.addEventListener(e,t,!1)}:window.attachEvent?function(e,t){this.attachEvent("on"+e,t)}:void 0}(),t.isTouchDevice=function(){return"ontouchstart"in window||"onmsgesturechange"in window},t.isNode=function(e){return"object"==typeof Node?e instanceof Node:e&&"object"==typeof e&&"number"==typeof e.nodeType&&"string"==typeof e.nodeName},t.isElement=function(e){return"object"==typeof HTMLElement?e instanceof HTMLElement:e&&"object"==typeof e&&null!==e&&1===e.nodeType&&"string"==typeof e.nodeName},t.WonderUIModule});