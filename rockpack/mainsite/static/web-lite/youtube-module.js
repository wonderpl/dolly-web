
/* ======================================= */
/*  UI Module for youtube videos on the Web Lite player
/*  Date: Thurs 9th January 2014
/* ======================================= */

(function(w,d){

    var _ = {
        data: window.videoData,

        // Status vars
        framecount: 0,
        newvolume: 100,
        currentvolume: 0,
        played: false,
        scrubbed: false,
        scrubbing: false,
        loaded: false,
        state: {
            playing: false,
            fullscreen: false
        },
        
        // UI vars
        mousedown: false,
        mousetarget: undefined,
        controlshovered: true,

        // Timing vars
        displayTime: '--:--',
        time: 0,
        duration: 00,
        timers: {
            seek: 11,
            buffer: 0,
            interaction: 0,
            vol: 0
        },

        UA: window.navigator.userAgent.toLowerCase(),
        elements: {}
    };

    _.WonderYTModule = function( elem, video, opts, data ) {
        _.data = data;
        _.player = new YT.Player(elem, {
            width: '100%',
            height: '100%',
            videoId: video,
            playerVars: opts,
            events: {
                'onReady': _.onContentReady,
                'onStateChange': _.onPlayerStateChange
            }
        });
        window.ytplayer = _.player;
        window.wonder = _;
        _.init();
        return _.player;
    };

    _.onPlayerStateChange = function (state) {
        // console.log( state );
    };

    // Update content, status and duration
    _.onContentReady = function () {
        _.time = _.player.getCurrentTime();    
        _.duration = _.data.video.duration;
        _.removeClass( _.elements.poster, 'loading' );
        _.elements.poster.getElementsByTagName('td')[0].innerHTML = (_.data.title.replace(/_/g,' '));
        setTimeout( function( ) {
            _.state.playing = false;
            _.hideLoader();
            _.loaded = true;
        }, 200);

    };

    // Add event listeners
    _.init = function () {

        _.ie8 = ( _.hasClass(document.querySelector('html'), 'ie8') ) ? true : false;
        _.ie10 = ( _.UA.indexOf('msie 1') !== -1 ) ? true : false;
        _.ipad = ( _.UA.indexOf('ipad') !== -1 ) ? true : false;
        _.ios = ( _.UA.indexOf('ipad') !== -1 || _.UA.indexOf('iphone') !== -1 ) ? true : false;

        // Cache our UI elements
        _.elements.wrapper = d.getElementById('wonder-wrapper');
        _.elements.controls = d.getElementById('wonder-controls');
        _.elements.poster = d.getElementById('wonder-poster');
        _.elements.loader = d.getElementById('wonder-loader');
        
        // Main buttons
        _.elements.playbutton = d.querySelector('.wonder-play');
        _.elements.bigplaybutton = d.querySelector('.wonder-play-big');
        _.elements.pausebutton = d.querySelector('.wonder-pause');
        _.elements.fullscreenbutton = d.querySelector('.wonder-fullscreen');
        _.elements.volumebutton = d.querySelector('.wonder-volume');
        _.elements.timer = d.querySelector('.wonder-timer');

        // Scrubber element groups
        _.elements.scrubbers = d.querySelectorAll('.scrubber');
        _.elements.scrubber_handles = d.querySelectorAll('.scrubber-handle');
        _.elements.scrubber_targets = d.querySelectorAll('.scrubber-target');
        _.elements.scrubber_trans = d.querySelectorAll('.scrubber-trans');

        // Scrubber specific elements
        _.elements.scrubber_vid = d.querySelector('.scrubber.vid');
        _.elements.scrubber_buffer = d.querySelector('.scrubber-buffer');
        _.elements.scrubber_progress_vid = d.querySelector('.scrubber-progress.vid');
        _.elements.scrubber_handle_vid = d.querySelector('.scrubber-handle.vid');
        _.elements.scrubber_vol = d.querySelector('.scrubber.vol');
        _.elements.scrubber_target_vol = d.querySelector('.scrubber-target.vol');
        _.elements.scrubber_progress_vol = d.querySelector('.scrubber-progress.vol');
        _.elements.scrubber_handle_vol = d.querySelector('.scrubber-handle.vol');
        _.elements.scrubber_timer = document.querySelector('.scrubber-timer');

        // Listen for user interaction and show and hide the nav as necessary
        if ( _.isTouchDevice() === false ) {
            _.listen(_.elements.wrapper, 'mousemove', _.interaction);
            _.listen(_.elements.controls, 'mousemove', _.interaction);
            _.listen(_.elements.poster, 'mousemove', _.interaction);
            _.listen(_.elements.loader, 'mousemove', _.interaction);
            _.listen(_.elements.playbutton, 'mousemove', _.interaction);
            _.listen(_.elements.bigplaybutton, 'mousemove', _.interaction);
            _.listen(_.elements.pausebutton, 'mousemove', _.interaction);
            _.listen(_.elements.fullscreenbutton, 'mousemove', _.interaction);
            _.listen(_.elements.volumebutton, 'mousemove', _.interaction);
            _.listen(_.elements.timer, 'mousemove', _.interaction);
            _.listen(_.elements.scrubbers, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_handles, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_targets, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_trans, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_vid, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_progress_vid, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_handle_vid, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_vol, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_progress_vol, 'mousemove', _.interaction);
            _.listen(_.elements.scrubber_handle_vol, 'mousemove', _.interaction);    
        }

        // Listen for interaction on the actual UI contols
        _.listen(_.elements.playbutton, 'click', _.play);
        _.listen(_.elements.bigplaybutton, 'click', _.play);
        _.listen(_.elements.pausebutton, 'click', _.pause);
        _.listen(_.elements.fullscreenbutton, 'click', _.fullscreen);
        _.listen(_.elements.volumebutton, 'click', _.volume);

        // Decide which listeners to use for the scrubbers.
        if ( _.isTouchDevice() ) {
            // _.listen(_.elements.loader, 'touchstart', function(e){event.preventDefault();});
            // _.listen(_.elements.loader, 'touchend', _.interaction);
            _.addClass(_.elements.controls, 'show');
            _.listen(_.elements.loader, 'click', _.toggleControls);
            _.listen(_.elements.scrubber_trans, 'touchmove', _.scrubTouch);
            _.listen(_.elements.scrubber_trans, 'touchstart', _.scrubDown);
            _.listen(_.elements.scrubber_trans, 'touchleave', _.scrubUp);
            _.listen(_.elements.scrubber_trans, 'touchend', _.scrubUp);
        } else {
            _.listen(_.elements.loader, 'click', _.togglePlay);
            _.listen(_.elements.scrubber_trans, 'mousemove', _.scrubMouse);
            _.listen(_.elements.scrubber_trans, 'mousedown', _.scrubDown);
            _.listen(_.elements.scrubber_trans, 'mouseup', _.scrubUp);
            _.listen(_.elements.scrubber_trans, 'mouseleave', _.scrubUp);
            
            _.listen(_.elements.controls, 'mouseleave', function(){
                _.controlshovered = false;
            });
            _.listen(_.elements.controls, 'mouseenter', function(){
                _.controlshovered = true;
            });
        }

        if ( _.ios === true ) {
            _.addClass( _.elements.controls, 'volume-disabled' );
        }

        Conduit.add('yttick', _.ytTick);
        Conduit.add('updateTimers', _.updateTimers);
        Conduit.add('bufferTick', _.bufferTick);
        if ( _.ie8 === false && _.flash === false ) {
            Conduit.add('moveBufferBar', _.moveBufferBar);    
        }
        Conduit.add('uiTick', _.uiTick);
        Conduit.add('actionTick', _.actionTick);
        if ( _.ie8 === true ) {
            Conduit.add('ieTick', _.ieTick);    
        }
        Conduit.start();
    };

    _.destroy = function() {
        try {
            Conduit.remove('yttick');
            Conduit.remove('updateTimers');
            Conduit.remove('bufferTick');
            Conduit.remove('moveBufferBar');
            Conduit.remove('uiTick');
            Conduit.remove('actionTick');
            Conduit.remove('ieTick');
            _.player.destroy();
        } catch (e) {}
    };

    _.onError = function (error, info) {
        // Info is an object with an error code
        // e.g. { "code": "stream" }

        // console.log(JSON.stringify(info));
        // console.log(JSON.stringify(error));
    };

    // Respond to the OO Message bus Play event
    _.onPlay = function () {
        if ( _.state.playing === false ) {
            _.addClass(_.elements.poster, 'hide');
            _.addClass(_.elements.playbutton, 'hidden');
            _.addClass(_.elements.bigplaybutton, 'hidden');
            _.removeClass(_.elements.pausebutton, 'hidden');
        }
        _.hideLoader();
        _.state.playing = true;
    };
    
    // Respond to the OO Message bus Pause event
    _.onPause = function () {
        if ( _.state.playing === true ) {
            _.removeClass(_.elements.playbutton, 'hidden');
            // _.removeClass(_.elements.bigplaybutton, 'hidden');
            _.addClass(_.elements.pausebutton, 'hidden');
            _.hideLoader();
            _.state.playing = false;
        }
    };

    _.onSeeked = function (e) {
        // console.log('onseeked event fired');
        _.scrubbed = false;
        if ( _.played === false ) {
            // _.mb.publish(OO.EVENTS.PLAY);    
            _.onPlay();
        }
    };

    _.onVolumeChanged = function (vol) {
        _.newvolume = vol;
    };

    _.onPlayed = function (e) {
        _.state.playing = false;
        _.played = true;
        _.removeClass(_.elements.playbutton, 'hidden');
        _.addClass(_.elements.pausebutton, 'hidden');
        _.removeClass( _.elements.poster, 'hide' );
        _.hideLoader();
    };

    _.togglePlay = function (e) {
        _.prevent(e);

        if ( _.loaded === true ) {
            if ( _.state.playing === true ) {
                _.pause();
            } else {
                _.play();
            }    
        }
    };

    // _.toggleControls = function (e) {
    //     _.prevent(e);
    //     if ( _.hasClass( _.elements.controls, 'show' ) ) {
    //         _.removeClass( _.elements.controls, 'show' );
    //         _.addClass( _.elements.controls, 'hide' );
    //     } else {
    //         _.removeClass( _.elements.controls, 'show' );
    //         _.addClass( _.elements.controls, 'show' );
    //     }
    // };

    /*  UI listener callbacks
    /* ======================================= */

    _.play = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.played = false;
            _.player.playVideo();
            // _.mb.publish(OO.EVENTS.PLAY);    
            _.onPlay();
        }
    };

    _.pause = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.player.pauseVideo();
            // _.mb.publish(OO.EVENTS.PAUSE);    
            _.onPause();
        }
    };

    _.volume = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.toggleClass( _.elements.scrubber_vol, 'vol-visible' );
            _.toggleClass( _.elements.scrubber_target_vol, 'vol-visible' );
        }
    };

    _.rewind = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            if ( (_.time-30) >= 0 && _.time !== 0 ) {
                _.seek(_.time-30);
            } else {
                _.seek(0);
            }    
        }
    };

    _.seek = function (seconds) {
        // _.mb.publish(OO.EVENTS.SEEK, seconds);
        _.player.seekTo( seconds );
    };

    _.fullscreen = function (e) {
        _.prevent(e); 
        if ( _.state.fullscreen === false ) {
            if ( _.ipad === true ) {
                _.elements.video.webkitEnterFullscreen();
                _.state.fullscreen = true;
            } else {
                // _.mb.publish(OO.EVENTS.FULLSCREEN_CHANGED);
                _.attemptFullscreen(_.elements.wrapper);
                _.addClass(_.elements.wrapper, 'fullscreen');
                _.state.fullscreen = true;
            }
        } else {
            if(document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
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

    // The scrubber has been clicked on
    _.scrubDown = function(e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            
            if ( _.mousetarget === 'vid' ) {
                _.play();
            }

            _.mousedown = true;
            _.scrubMouse(e);
            _.oldtime = _.time;
        }
    };

    // Mouse released from the scrubber ( Don't prevent default or everything will break! )
    _.scrubUp = function(e) {
        _.prevent(e);
        if (  _.loaded === true && _.mousedown === true ) {
            _.mousedown = false;
            if ( _.mousetarget === 'vid' ) {
                _.play();
            } 
            _.mousetarget = undefined;
        }
    };

    _.scrubMouse = function(e) {
        if ( _.mousedown === true && _.loaded === true ) {
            _.prevent(e);

            var x = e.clientX,
                y = e.clientY,
                target = e.srcElement || e.target,
                percentage,
                scrubtype = target.className.replace('scrubber-trans ','');

            clearTimeout( _.seekTimeout );
            _.seekTimeout = setTimeout(function(){

                if ( scrubtype === 'vid' ) {
                    var rect = _.elements.scrubber_vid.getBoundingClientRect();
                    percentage = x - rect.left;
                    percentage = ((percentage/(rect.right - rect.left)) * 100 );                    
                    if ( percentage <= 0 ) {
                        _.scrubVid(0);                        
                    } else if ( percentage >= 100 ) {
                        _.scrubVid(100);
                    } else {
                        _.scrubVid(percentage);    
                    }
                } else if ( scrubtype === 'vol' ) {
                    var rect = _.elements.scrubber_vol.getBoundingClientRect();
                    percentage = y - rect.bottom;
                    percentage = ((percentage/(rect.bottom - rect.top)) * 100 );
                    if ( percentage <= -100 ) {
                        _.scrubVol(100);                        
                    } else if ( percentage >= 0 ) {
                        _.scrubVol(0);
                    } else {
                        _.scrubVol(Math.abs(percentage));    
                    }
                }

            },10);
            
            return false;
        }
    };

    _.scrubTouch = function(e) {
        if ( _.mousedown === true && _.loaded === true ) {
            _.prevent(e);
            var pos = e.touches[0] || e.changedTouches[0],
                target = e.srcElement || e.target,
                x = pos.pageX,
                y = pos.pageY,
                percentage,
                scrubtype = target.className.replace('scrubber-trans ','');

            clearTimeout( _.seekTimeout );
            _.seekTimeout = setTimeout(function(){

                if ( scrubtype === 'vid' ) {
                    var rect = _.elements.scrubber_vid.getBoundingClientRect();
                    percentage = x - rect.left;
                    percentage = ((percentage/(rect.right - rect.left)) * 100 );
                    if ( percentage <= 0 ) {
                        _.scrubVid(0);                        
                    } else if ( percentage >= 100 ) {
                        _.scrubVid(100);
                    } else {
                        _.scrubVid(percentage);    
                    }
                } else if ( scrubtype === 'vol' ) {
                    var rect = _.elements.scrubber_vol.getBoundingClientRect();
                    percentage = y - rect.bottom;
                    percentage = ((percentage/(rect.bottom - rect.top)) * 100 );
                    if ( percentage <= -100 ) {
                        _.scrubVol(100);                        
                    } else if ( percentage >= 0 ) {
                        _.scrubVol(0);
                    } else {
                        _.scrubVol(Math.abs(percentage));    
                    }
                }

            },10);

            return false;
        }
    };

    _.scrubVid = function(percentage) {
        _.pause();
        _.scrubbed = true;
        _.mousetarget = 'vid';
        _.timers.seek = 0;
        _.newtime = (_.duration / 100) * percentage;
        _.videoPercentage = percentage;
    };

    _.scrubVol = function(percentage) {
        _.mousetarget = 'vol';
        _.player.setVolume(percentage);
        _.onVolumeChanged(percentage);
    };

    _.showLoader = function () {
        _.addClass( _.elements.scrubber_vid, 'loading' );
        _.addClass( _.elements.scrubber_buffer, 'hide' );
        _.addClass( _.elements.scrubber_timer, 'show' );
        _.elements.loader.className = 'show';
    };

    _.hideLoader = function () {
        _.removeClass( _.elements.scrubber_vid, 'loading' );
        _.removeClass( _.elements.scrubber_buffer, 'hide' );
        _.removeClass( _.elements.scrubber_timer, 'show' );
        _.elements.loader.className = '';
    };

    // Show the controls
    _.showUI = function () {
        _.addClass( _.elements.controls, 'show' );
        _.removeClass( _.elements.controls, 'hide' );
    };

    _.hideUI = function () {
        _.addClass( _.elements.controls, 'hide' );
        _.removeClass( _.elements.controls, 'show' );
        _.removeClass( _.elements.scrubber_vol, 'vol-visible' );   
        _.removeClass( _.elements.scrubber_target_vol, 'vol-visible' );   
    };

    // A user interaction has been detected, show the UI and 
    // set a timer to hide it again
    _.interaction = function () {
        if ( _.controlshovered === false ) {
            _.showUI();
            _.timers.interaction = 0;            
        }
    };

    _.actionTick = function () {
        if ( _.timers.seek === 10 ) {
            _.seek( _.newtime );    
            _.time = _.newtime;
        }
    };

    _.uiTick = function () {

        if ( _.scrubbed === true ) {
            _.elements.scrubber_progress_vid.style.width = _.videoPercentage + '%';
            _.elements.scrubber_handle_vid.style.left = _.videoPercentage + '%';
            _.elements.scrubber_timer.style.left = _.videoPercentage + '%';
            _.elements.scrubber_timer.innerHTML = _.getTime( _.newtime );
            _.showLoader();
        } else if ( _.loaded === true && _.time !== undefined && _.scrubbed === false && _.timers.seek > 60 ) {
            var percentage = ( (_.time/_.duration) * 100 ) + '%';        
            _.elements.scrubber_progress_vid.style.width = percentage;
            _.elements.scrubber_handle_vid.style.left = percentage;
            _.elements.scrubber_timer.style.left = percentage;
            _.elements.scrubber_timer.innerHTML = _.getTime( _.time );
        }
        
        // Check if the volume has changed
        if ( _.currentvolume != _.newvolume ) {
            _.currentvolume = _.newvolume;

            if ( _.newvolume === 0 ) {
                _.elements.volumebutton.className = 'volume wonder-volume vol-0';
            } else if ( _.newvolume > 0 && _.newvolume <= 33 ) {
                _.elements.volumebutton.className = 'volume wonder-volume vol-1';
            } else if ( _.newvolume > 33 && _.newvolume <= 65 ) {
                _.elements.volumebutton.className = 'volume wonder-volume vol-2';
            } else {
                _.elements.volumebutton.className = 'volume wonder-volume vol-3';
            }

            _.elements.scrubber_progress_vol.style.height = ( _.newvolume ) + '%';
            _.elements.scrubber_handle_vol.style.bottom = (( _.newvolume )-15) + '%';
        }

        // Update the time
        if ( _.state.playing === false ) {
            _.displayTime = _.getTime(_.duration);
        } else {    
            _.displayTime = _.getTime(_.time);
        }
        _.elements.timer.innerHTML = _.displayTime;

        if ( _.timers.interaction === 80 ) {
            if ( _.isTouchDevice() === false && _.controlshovered === false ) {
                _.hideUI();         
            }
        }
    };

    _.bufferTick = function () {
        if ( _.state.playing === true ) {
            _.timers.buffer++;
        }
        if ( _.timers.buffer === 60 ) {
            _.showLoader();
        }
    };

    _.moveBufferBar = function () {
        if ( _.timers.buffer === 10 && _.loaded === true && _.buffer !== undefined ) {
            var percentage = ( (_.buffer/_.duration) * 100 ) + '%';
            _.elements.scrubber_buffer.style.width = percentage;            
        }
    };

    _.ieTick = function () {
        var ww = _.ww();
        if ( !('width' in _) || _.width != ww ) {
            if ( ww <= 480 ) {
                // Mobile
                _.elements.wrapper.className = 'mobile';
            } else if ( ww > 480 && ww <= 959 ) {
                // Tablet
                _.elements.wrapper.className = 'tablet';
            } else if ( ww >= 960 && ww <= 1023 ) {
                // Desktop
                _.elements.wrapper.className = 'desktop';
            } else {
                // Widescreen
                _.elements.wrapper.className = 'widescreen';
            }
        }
        _.width = ww;
    };

    _.updateTimers = function () {
        _.timers.seek++;
        _.timers.interaction++;
        _.framecount++;
    };

    _.ytTick = function () {
        if ( _.loaded === true ) { 
            if ( 'getCurrentTime' in _.player ) {
                var time = _.player.getCurrentTime();
            }

            if ( time != _.time && _.scrubbed === true ) {
                setTimeout( function(){
                    _.scrubbed = false;
                }, 150);
            }
            _.time = time;
            if ( _.time !== 0 && _.time !== undefined ) {
                _.timers.buffer = 0;
                _.hideLoader();            
            }       
        }
    };

    _.Tick = function () {

        // // Because we don't have the Ooyala message bus, we need to make our on OnTimeUpdate ticker
        // _.YTTick();

        // // Increment our timers
        // _.timers.seek++;
        // _.timers.interaction++;
        // _.framecount++;

        // _.BufferTick();
        // _.UITick();
        // _.ActionTick();
        // _.IETick();
        // requestAnimationFrame( _.Tick );
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

    _.toggleClass = function( el, cl ) {
        if ( _.hasClass( el, cl ) === true ) {
            _.removeClass( el, cl );
        } else {
            _.addClass( el, cl );
        }
    }

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

    // Returns true if touch events are present
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

    // Cookier setter
    _.setCookie = function ( name, val, life) {
        var d = new Date();
        d.setTime(d.getTime()+(life*24*60*60*1000));
        var expires = "expires="+d.toGMTString();
        document.cookie = name + "=" + val+ "; " + expires;
    };

    // Cookie getter
    _.getCookie = function ( cname ) {
        var name = cname + "=";
        var ca = document.cookie.split(';');
        for (var i=0; i<ca.length; i++) {
            var c = ca[i].trim();
            if (c.indexOf(name)==0) return c.substring(name.length,c.length);
        }
        return "";
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

    // Window width polyfill
    _.ww = (function () {
       if (typeof window.innerWidth !== 'undefined') {
           return function() {
               return window.innerWidth;
           };
       } else {
            var b = 'clientWidth' in document.documentElement ? document.documentElement : document.body;
            return function() {
                return b.clientWidth;
            };
       }
    })();

    window.WonderYTModule = _.WonderYTModule;

})(window,document);