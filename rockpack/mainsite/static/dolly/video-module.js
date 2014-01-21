
/* ======================================= */
/*  RequestAnimationFrame polyfill ( Courtesy of Paul Irish )
/*  Date: Thurs 9th January 2014
/* ======================================= */

(function() {
    var lastTime = 0;
    var vendors = ['webkit', 'moz'];
    for(var x = 0; x < vendors.length && !window.requestAnimationFrame; ++x) {
        window.requestAnimationFrame = window[vendors[x]+'RequestAnimationFrame'];
        window.cancelAnimationFrame =
          window[vendors[x]+'CancelAnimationFrame'] || window[vendors[x]+'CancelRequestAnimationFrame'];
    }
    if (!window.requestAnimationFrame)
        window.requestAnimationFrame = function(callback, element) {
            var currTime = new Date().getTime();
            var timeToCall = Math.max(0, 16 - (currTime - lastTime));
            var id = window.setTimeout(function() { callback(currTime + timeToCall); },
              timeToCall);
            lastTime = currTime + timeToCall;
            return id;
        };
    if (!window.cancelAnimationFrame)
        window.cancelAnimationFrame = function(id) {
            clearTimeout(id);
        };
}());

/* ======================================= */
/*  Custom Wonder UI module for the Ooyala player
/*  Date: Thurs 9th January 2014
/* ======================================= */

OO.plugin("WonderUIModule", function (OO) {

    var _ = {
        elements: {},
        mousedown: false,
        scrubbed: false,
        seekTimeout: undefined,
        loaderTimeout: undefined
    };

    // This section contains the HTML content to be used as the UI
    // '<a href="#" class="rewind wonder-rewind icon-ccw"></a>' +
    var wonder_template = 
        '<div id="wonder-poster">' +
            '<img src="/static/assets/wonderplayer/img/trans.png" alt="" id="wonder-poster" class="blur"/>' +
            '<span class="f-thin f-uppercase"></span>' +
        '</div>' +
        '<a href="#" id="wonder-loader" class="show"></a>' + 
        '<div id="wonder-controls">' + 
            '<a href="#" class="play wonder-play player-icon-play"></a>' + 
            '<a href="#" class="pause wonder-pause player-icon-pause hidden"></a>' + 
            '<a href="#" class="volume wonder-volume vol-high"></a>' +
            '<a href="#" class="wonder-logo"></a>' +
            '<a href="#" class="fullscreen wonder-fullscreen player-icon-fullscreen"></a>' +
            '<span class="wonder-timer">--:--</span>' +
            '<div class="scrubber vid">' +
                '<div class="scrubber-progress vid"></div>' +
                '<a href="#" class="scrubber-handle vid player-icon-circle"></a>' +
            '</div>' +
            '<div class="scrubber-target vid">' +
                '<img src="/static/assets/wonderplayer/img/trans.png" class="scrubber-trans vid" width="100%" height="100%" />' +
            '</div>' +

            '<div class="scrubber vol">' +
                '<div class="scrubber-progress vol"></div>' +
                '<a href="#" class="scrubber-handle vol player-icon-circle"></a>' +
            '</div>' +
            '<div class="scrubber-target vol">' +
                '<img src="/static/assets/wonderplayer/img/trans.png" class="scrubber-trans vol" width="100%" height="100%" />' +
            '</div>' +

        '</div>';

    // Constructor
    _.WonderUIModule = function (mb, id) {
        _.mb = mb; // save message bus reference for later use
        _.id = id;
        _.init();
    };

    // Add event listeners
    _.init = function () {

        _.state = {
            playing: false,
            fullscreen: false
        };

        // Initial listeners
        _.mb.subscribe(OO.EVENTS.PLAYER_CREATED, 'wonder', _.onPlayerCreate);
        _.mb.subscribe(OO.EVENTS.PLAYHEAD_TIME_CHANGED, 'wonder', _.onTimeUpdate);
        _.mb.subscribe(OO.EVENTS.CONTENT_TREE_FETCHED, 'wonder', _.onContentReady);
        _.mb.subscribe(OO.EVENTS.VOLUME_CHANGED, 'wonder', _.onVolumeChanged);
        _.mb.subscribe(OO.EVENTS.PLAYED, 'wonder', _.onPlayed);
        _.mb.subscribe(OO.EVENTS.PAUSE, 'wonder', _.onPause);
        _.mb.subscribe(OO.EVENTS.PLAY, 'wonder', _.onPlay);
        _.mb.subscribe(OO.EVENTS.PLAYER_EMBEDDED, 'wonder', _.hideLoader);

        window.wonderPlayer = this;
        window.wonder = _;
    };

    /*  Message bus event subscriber callbacks
    /* ======================================= */

    // Build the UI
    _.onPlayerCreate = function (event, elementId, params) {
        _.wrapper = document.createElement('div');
        _.wrapper.setAttribute('id','wonder-wrapper');
        _.wrapper.innerHTML = wonder_template;
        _.playerElem = document.getElementById(elementId);
        _.playerElem.parentNode.insertBefore(_.wrapper, _.playerElem);
        _.wrapper.insertBefore(_.playerElem, document.getElementById('wonder-poster'));


        // Cache our UI elements
        _.elements.wrapper = document.getElementById('wonder-wrapper');
        _.elements.controls = document.getElementById('wonder-controls');
        _.elements.poster = document.getElementById('wonder-poster');
        _.elements.loader = document.getElementById('wonder-loader');
        
        _.elements.playbutton = document.querySelector('.wonder-play');
        _.elements.pausebutton = document.querySelector('.wonder-pause');
        _.elements.fullscreenbutton = document.querySelector('.wonder-fullscreen');
        _.elements.volumebutton = document.querySelector('.wonder-volume');
        _.elements.timer = document.querySelector('.wonder-timer');

        // Scrubber element groups
        _.elements.scrubbers = document.querySelectorAll('.scrubber');
        _.elements.scrubber_handles = document.querySelectorAll('.scrubber-handle');
        _.elements.scrubber_targets = document.querySelectorAll('.scrubber-target');
        _.elements.scrubber_trans = document.querySelectorAll('.scrubber-trans');

        // Scrubber specific elements
        _.elements.scrubber_progress_vid = document.querySelector('.scrubber-progress.vid');
        _.elements.scrubber_handle_vid = document.querySelector('.scrubber-handle.vid');
        _.elements.scrubber_progress_vol = document.querySelector('.scrubber-progress.vol');
        _.elements.scrubber_handle_vol = document.querySelector('.scrubber-handle.vol');

        // // Add some UI event listeners   
        _.listen(_.elements.playbutton, 'click', _.play);
        _.listen(_.elements.pausebutton, 'click', _.pause);
        _.listen(_.elements.fullscreenbutton, 'click', _.fullscreen);
        _.listen(_.elements.volumebutton, 'click', _.volume);
        _.listen(_.elements.loader, 'click', _.togglePlay);

        if ( _.isTouchDevice() ) {
            _.addClass(_.elements.controls, 'touch');
            _.listen(_.elements.scrubber_trans, 'touchmove', _.scrubTouch);
            _.listen(_.elements.scrubber_trans, 'touchstart', _.scrubDown);
            _.listen(_.elements.scrubber_trans, 'touchleave', _.scrubUp);
            _.listen(_.elements.scrubber_trans, 'touchend', _.scrubUp);
        } else {
            _.listen(_.elements.scrubber_trans, 'mousemove', _.scrubMouse);
            _.listen(_.elements.scrubber_trans, 'mousedown', _.scrubDown);
            _.listen(_.elements.scrubber_trans, 'mouseup', _.scrubUp);
            _.listen(_.elements.scrubber_trans, 'mouseleave', _.scrubUp);
        }
    };

    // Update content, status and duration
    _.onContentReady = function (event, content) {
        _.info = content;
        _.elements.poster.getElementsByTagName('img')[0].src = content.promo || content.promo_image;
        _.elements.loader.className = '';
        _.elements.poster.getElementsByTagName('span')[0].innerHTML = (_.info.title.replace(/_/g,' '));
        _.duration = content.duration;
    };
    
    _.onTimeUpdate = function (event, time, duration, buffer, seekrange) {
        _.time = time;
        _.duration = duration;

        if ( _.state.playing === false ) {
            _.displayTime = _.getTime(_.duration);
        } else {
            _.displayTime = _.getTime(_.time);
        }

        _.elements.timer.innerHTML = _.displayTime;

        if ( _.state.playing === true && _.mousedown === false ) {
            requestAnimationFrame(_.tick);
        } else {
            cancelAnimationFrame(_.tick);
        }
    };

    _.onPlay = function () {
        if ( _.state.playing === false ) {
            _.addClass(_.elements.poster, 'hide');
            _.addClass(_.elements.playbutton, 'hidden');
            _.removeClass(_.elements.pausebutton, 'hidden');
            _.state.playing = true;
        }
    };

    _.onPause = function () {
        if ( _.state.playing === true ) {
            _.removeClass(_.elements.playbutton, 'hidden');
            _.addClass(_.elements.pausebutton, 'hidden');
            _.hideLoader();
            _.state.playing = false;
        }
    };

    _.onVolumeChanged = function (e, vol) {
        _.volume = vol;
        
        if ( vol <= 0.2 ) {
            _.removeClass( _.elements.volumebutton, 'medium' );
            _.addClass( _.elements.volumebutton, 'mute' );
        } else if ( vol > 0.2 && vol <= 0.65 ) {
            _.removeClass( _.elements.volumebutton, 'mute' );    
            _.addClass( _.elements.volumebutton, 'medium' );
        } else {
            _.removeClass( _.elements.volumebutton, 'mute' );
            _.removeClass( _.elements.volumebutton, 'medium' );
        }
        
        _.elements.scrubber_progress_vol.style.width = ( vol * 100 ) + '%';
        _.elements.scrubber_handle_vol.style.left = ( vol * 100 ) + '%';
    };

    _.onPlayed = function () {
        _.state.playing = false;
        _.removeClass(_.elements.playbutton, 'hidden');
        _.addClass(_.elements.pausebutton, 'hidden');
        cancelAnimationFrame( _.tick );
        clearTimeout( _.loaderTimeout );
        _.hideLoader();
    };

    _.togglePlay = function (e) {
        _.prevent(e);
        if ( _.state.playing === true ) {
            _.pause();
        } else {
            _.play();
        }
    };

    /*  UI listener callbacks
    /* ======================================= */

    _.play = function (e) {
        _.prevent(e);
        _.mb.publish(OO.EVENTS.PLAY);
    };

    _.pause = function (e) {
        _.prevent(e);
        _.mb.publish(OO.EVENTS.PAUSE);
    };

    _.volume = function (e) {
        _.prevent(e);
        if ( _.volume > 0 ) {
            _.mb.publish(OO.EVENTS.CHANGE_VOLUME,0);
        } else {
            _.mb.publish(OO.EVENTS.CHANGE_VOLUME,1);
        }
        // if ( _.hasClass( _.elements.volumebutton, 'vol-high' ) ) {
        //     _.mb.publish(OO.EVENTS.CHANGE_VOLUME,.5);
        //     _.elements.volumebutton.className = _.elements.volumebutton.className.replace('vol-high','vol-medium');
        // } else if ( _.hasClass( _.elements.volumebutton, 'vol-medium' ) ) {
        //     _.mb.publish(OO.EVENTS.CHANGE_VOLUME,.2);
        //     _.elements.volumebutton.className = _.elements.volumebutton.className.replace('vol-medium','vol-low');
        // } else if ( _.hasClass( _.elements.volumebutton, 'vol-low' ) ) {
        //     _.mb.publish(OO.EVENTS.CHANGE_VOLUME,1);
        //     _.elements.volumebutton.className = _.elements.volumebutton.className.replace('vol-low','vol-high');
        // }
    };

    _.rewind = function (e) {
        _.prevent(e);
        if ( (_.time-30) >= 0 && _.time !== 0 ) {
            _.seek(_.time-30);
        } else {
            _.seek(0);
        }
    };

    _.seek = function (seconds) {
        // _.elements.loader.className = 'show';
        _.mb.publish(OO.EVENTS.SEEK, seconds);
        _.mb.publish(OO.EVENTS.PLAY);
    };

    _.fullscreen = function (e) {
        _.prevent(e);
        if ( _.state.fullscreen === false ) {
            _.mb.publish(OO.EVENTS.FULLSCREEN_CHANGED);
            _.attemptFullscreen(_.elements.wrapper);
            _.addClass(_.elements.wrapper, 'fullscreen');
            _.state.fullscreen = true;
        } else {
            if(document.exitFullscreen) {
                document.exitFullscreen();
            } else if(document.mozExitFullScreen) {
                document.mozExitFullScreen();
            } else if(document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if(document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            }
            _.removeClass(_.elements.wrapper, 'fullscreen');
            _.state.fullscreen = false;
        }
    };

    _.scrubMouse = function(e) {
        if ( _.mousedown === true ) {
            _.prevent(e);

            var x = e.clientX,
                target = e.srcElement || e.target,
                percentage,
                scrubtype = target.className.replace('scrubber-trans ','');

            clearTimeout( _.seekTimeout );
            _.seekTimeout = setTimeout(function(){
                percentage = x - target.getBoundingClientRect().left;
                percentage = ((percentage/target.clientWidth ) * 100 );
                if ( scrubtype === 'vid' ) {
                    _.scrubVid(percentage);
                } else if ( scrubtype === 'vol' ) {
                    _.scrubVol(percentage);
                }
            },10);
            
            return false;
        }
    };

    _.scrubTouch = function(e) {
        if ( _.mousedown === true ) {
            _.prevent(e);
            var pos = e.touches[0] || e.changedTouches[0],
                x = pos.pageX,
                percentage;

            clearTimeout( _.seekTimeout );
            _.seekTimeout = setTimeout(function(){
                percentage = pos.pageX - _.elements.scrubber.getBoundingClientRect().left;
                percentage = ((percentage / _.elements.scrubber.clientWidth ) * 100 );

                if ( percentage >= 0 && percentage <= 100 ) {
                    _.seek( (_.duration / 100) * percentage );
                    _.elements.scrubber_progress.style.width = percentage + '%';
                    _.elements.scrubber_handle.style.left = percentage + '%';    
                } else {
                    _.scrubUp();
                }
                
            },10);

            return false;
        }
    };

    // The scrubber has been clicked on
    _.scrubDown = function(e) {
        _.prevent(e);
        _.mousedown = true;
        _.old_time = _.time;
        _.addClass(_.elements.scrubber_handles, 'down');
    };

    // Mouse released from the scrubber ( Don't prevent default or everything will break! )
    _.scrubUp = function(e) {
        _.prevent(e);
        if ( _.mousedown === true ) {
            _.mousedown = false;
            _.removeClass(_.elements.scrubber_handles, 'down');            
        }
    };

    _.scrubVid = function(percentage) {
        _.seek( (_.duration / 100) * percentage );
        _.elements.scrubber_progress_vid.style.width = percentage + '%';
        _.elements.scrubber_handle_vid.style.left = percentage + '%';
    };

    _.scrubVol = function(percentage) {
        _.mb.publish(OO.EVENTS.CHANGE_VOLUME, percentage/100);
    };

    _.showLoader = function () {
        clearTimeout( _.loaderTimeout );
        _.elements.loader.className = 'show';
    };

    _.hideLoader = function () {
        clearTimeout( _.loaderTimeout );
        _.elements.loader.className = '';
    };

    _.tick = function () {
        var percentage = ( (_.time/_.duration) * 100 ) + '%';
        
        _.elements.scrubber_progress_vid.style.width = percentage;
        _.elements.scrubber_handle_vid.style.left = percentage;
        _.elements.loader.className = '';

        clearTimeout( _.loaderTimeout );
        _.loaderTimeout = setTimeout( function() {
            if ( _.state.playing === true ) {
                _.elements.loader.className = 'show';
            }
        }, 250);
    };

    /*  Utility Functions
    /* ======================================= */

    // Find the right method, call on correct element
    _.attemptFullscreen = function(el) {
        if(el.requestFullscreen) {
            el.requestFullscreen();
        } else if(el.mozRequestFullScreen) {
            el.mozRequestFullScreen();
        } else if(el.webkitRequestFullscreen) {
            el.webkitRequestFullscreen();
        } else if(el.msRequestFullscreen) {
            el.msRequestFullscreen();
        } 
        // else if (el.getElementsByTagName('video')[0].webkitEnterFullscreen){
            // el.getElementsByTagName('video')[0].webkitEnterFullscreen();
        // }
    };

    // Returns a boolean of whether the class is present or not
    _.hasClass = function ( el, cl ) {
        return el.className.indexOf(cl) === -1 ? false : true;
    };

    // If class is not present, add it
    _.addClass = function ( el, cl ) {
        var els = _.select(el);
        for ( var i = 0; i < els.length; i++ ) {
            if ( els[i].className.indexOf(cl) === -1 ) {
                els[i].className += (els[i].className.length === 0 ? '' :  ' ') + cl;
            }
        };
    };

    // If class is present, remove it
    _.removeClass = function ( el, cl ) {
        var els = _.select(el);

        for ( var i = 0; i < els.length; i++ ) {
            if ( els[i].className.indexOf( cl ) !== -1 ) {
                if ( els[i].className.indexOf( cl + ' ' ) !== -1 ) {
                    els[i].className = els[i].className.replace( cl + ' ', '' );         
                } else if ( els[i].className.indexOf( ' ' + cl ) !== -1 ) {
                    els[i].className = els[i].className.replace( ' ' + cl, '' );
                } else if ( els[i].className.length === cl.length ) {
                    els[i].className = '';
                }
            }    
        };
    };

    // Simple object extender
    _.extend = function (obj, ext) {
        for (var prop in ext) {
            obj[prop] = (obj.hasOwnProperty(prop)) ? obj[prop] : ext[prop];
        }
        return obj;
    };

    _.getTime = function (d) {
        d = Number(d);
        var h = Math.floor(d / 3600);
        var m = Math.floor(d % 3600 / 60);
        var s = Math.floor(d % 3600 % 60);
        return ((h > 0 ? h + ":" : "") + (m > 0 ? (h > 0 && m < 10 ? "0" : "") + m + ":" : "0:") + (s < 10 ? "0" : "") + s);
    };

    // Prevents default behaviour of events
    _.prevent = function (e) {
        if ( typeof e !== 'undefined' ) {
            if (e.preventDefault) {
                e.preventDefault();
            } else if (e.stopPropagation) {
                e.stopPropagation();
            } else {
                e.returnValue = false;
            }            
        }
    };

    // Primitive selector engine
    _.select = function (target) {
        var arr;
        if (typeof target === 'string') {
            if (target.indexOf('#') !== -1) {
                return [document.getElementById(target.split('#')[1])];
            } else if (target.indexOf('.') !== -1) {
                arr = Array.prototype.slice.call(document.querySelectorAll(target));
                return (arr.length > 0) ? arr : null;
            } else {
                arr = Array.prototype.slice.call(document.getElementsByTagName(target));
                return (arr.length > 0) ? arr : null; 
            }
        } else if (_.isNode(target) || _.isElement(target) ) {
            return [target];
        } else if (typeof target === 'object') {
            try {
                return (target.length > 0 ) ? Array.prototype.slice.call(target) : null;    
            } catch(e){
                return target;
            }
            
        }
    };

    // Event handler
    _.listen = function (el, ev, fn) {
        var els = _.select(el);

        for ( var i = 0; i < els.length; i++ ) {
            _.attach.call(els[i], ev, fn);
        }
    };

    // Used by _.listen to choose the appropriate event listener
    _.attach = (function (ev, fn) {
        if (window.addEventListener) {
            return function(ev, fn) {
                this.addEventListener(ev, fn, false);    
            };
        } else if (window.attachEvent) {
            return function(ev, fn) {
                this.attachEvent('on' + ev, fn);
            };
        }
    })();

    _.isTouchDevice = function () {
        return 'ontouchstart' in window || 'onmsgesturechange' in window;
    };

    //Returns true if it is a DOM node
    _.isNode = function (o){
      return (
        typeof Node === "object" ? o instanceof Node : 
        o && typeof o === "object" && typeof o.nodeType === "number" && typeof o.nodeName==="string"
      );
    }

    //Returns true if it is a DOM element    
    _.isElement = function (o){
      return (
        typeof HTMLElement === "object" ? o instanceof HTMLElement : //DOM2
            o && typeof o === "object" && o !== null && o.nodeType === 1 && typeof o.nodeName==="string"
        );
    }

    return _.WonderUIModule;
});