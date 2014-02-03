
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
        volume: 1,
        newvolume: 1,

        played: false,
        scrubbed: false,
        scrubbing: false,
        loaded: false,

        seekTimeout: undefined,
        loaderTimeout: undefined,
        volumeTimeout: undefined,
        videoTimeout: undefined,
        interactionTimeout: undefined,

        videoUpdate: false,
        mousedown: false,
        mousetarget: undefined,        
        displayTime: '--:--',
        time: 0,
        duration: NaN
    };

    // This section contains the HTML content to be used as the UI
    // '<a href="#" class="rewind wonder-rewind icon-ccw"></a>' +
    // '<span class="f-thin f-uppercase"></span>' +
    var wonder_template = 
        '<div id="wonder-poster" class="loading">' +
            '<img src="/static/assets/wonderplayer/img/trans.png" alt="" id="wonder-poster" class="blur"/>' +
            '<table width="100%" height="100%" cellpadding="0" cellspacing="0"><tr><td width="100%" height="100%" align="center" valign="middle">Your video is loading</td></tr></table>' +
        '</div>' +
        '<a id="wonder-loader" class="show f-sans f-uppercase"><span>Your video is loading</span></a>' + 
        '<a class="wonder-play-big"></a>' + 
        '<div id="wonder-controls">' + 
            '<a class="play wonder-play player-icon-play"></a>' + 
            '<a class="pause wonder-pause player-icon-pause hidden"></a>' + 
            '<a class="volume wonder-volume vol-3">' +
                '<img class="vol-1" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAoCAYAAABq13MpAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAGBJREFUeNrs17EJgFAMBND/HcZacC+ntLJyo5gRxEYO3sGVgVeEQGZVjbQsIzDQ0NDQ0NDQ0NDQ0Jnoq7unodfukbge55eh+eNju3XvNLTrAQ0NDQ0NDQ0NDQ39Lo8AAwCo8wyaUULIQwAAAABJRU5ErkJggg==" />' +
                '<img class="vol-2" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAoCAYAAABq13MpAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAATNJREFUeNrsmLFKA0EQhnOaQlKo4APEwkIQsRILX8BO0iZV0BfIS1ilsbC2UcFW0EJs1CdQLKxTBCs9bEzwcP2OXGBykOOu2lmYHz7YKRa+O2Z3joucc7XQslALMCZt0iZt0iZt0vPyBCewXnlnOsY9EbtJfqEPjbJ7I4/fHjGsiPoFDuBDc3tcwo+od+AWGprbI6UJz242Z5rbY5oleID9rE5gG941X3kjaItWqcNRCPf0AK5FfRjKcLkT642iA6lJeijWEayFIJ1/s0kI0rti/V00ZLRIL0JX1I/pCNEu3csO3zQXmidiSgcSMRHfoF60x6fsFlzlRvgY9jSP8S9YFfUfHMO55q+819wDtMoI+5a+h084hU24KbvRZ3sswzijUiL7a2rSJm3SJm3SJk3+BRgA8LFe4j8YonoAAAAASUVORK5CYII=" />' +
                '<img class="vol-3" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAoCAYAAABq13MpAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAbhJREFUeNrs2c8rRFEUB/B53qSYaRYyVopSimTBhJRZ2diJlLAQs1IWFkr5H6xYYKOslGKNJfm5YGespPGzEDUZmeb53rq3jjtvyu6dU3PqU+dMM/U16d33zjie54WkVUVIYAUdug/WISEpdAxScA7HMCjt36MHdmAfGjiHvoc767V+uISBkp9SV4+AuTAOGe9v5WHK7zMcQhsxWLGCF/QfxDa0MQHfJLjqu+l7HKaHi7qKbIOr51togRznw2UXFsjcCPNmcBgf4w7s6auJqiw0wwPnY1x9m7OQ13ME5iTce1zDFpknISzhhmmV9LWQlBD6CJ7JLCJ0AU7InJByP31F+lYpoZ9IH5cS+oP0USmhq0j/KSV0PenfpIRuI/2NhNAqY5LMFxJCq8B1ZD6QEHqG9C9wyD10OwyTeQN+ON9Pu/r4NoucL2iCR87f9KK1eVpSgbmsEPyM6idxU2mo5vw0ntI7D1NZ6OC6QojCms/CZojj3qMSpn02TDkY47hh6oJXr7gy9oKGCvrqEYca6wlcLWk64VTCqlftp3thxHomLKpwwEHfYRk24ezfW5zyD0Xl0KXrV4ABABBpntz13cW2AAAAAElFTkSuQmCC" />' +
            '</a>' +
            '<a class="wonder-logo"></a>' +
            '<a class="fullscreen wonder-fullscreen player-icon-fullscreen"></a>' +
            '<span class="wonder-timer">--:--</span>' +
            '<div class="scrubber vid">' +
                '<div class="scrubber-progress vid"></div>' +
                '<a class="scrubber-handle vid player-icon-circle"></a>' +
            '</div>' +
            '<div class="scrubber-target vid">' +
                '<img src="/static/assets/wonderplayer/img/trans.png" class="scrubber-trans vid" width="100%" height="100%" />' +
            '</div>' +
            '<div class="scrubber vol">' +
                '<div class="scrubber-progress vol"></div>' +
                '<a class="scrubber-handle vol player-icon-circle"></a>' +
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

        if ( window.navigator.userAgent.toLowerCase().indexOf('ipad') !== -1 ) {
            _.ipad = true;
        }

        // Initial listeners
        // _.mb.subscribe('*', 'wonder', function(eventName){
        //     console.log(eventName);
        // });

        _.mb.subscribe(OO.EVENTS.PLAYER_CREATED, 'wonder', _.onPlayerCreate);
        _.mb.subscribe(OO.EVENTS.SEEKED, 'wonder', _.onSeeked);
        _.mb.subscribe(OO.EVENTS.CONTENT_TREE_FETCHED, 'wonder', _.onContentReady);
        _.mb.subscribe(OO.EVENTS.PLAYHEAD_TIME_CHANGED, 'wonder', _.onTimeUpdate);
        _.mb.subscribe(OO.EVENTS.VOLUME_CHANGED, 'wonder', _.onVolumeChanged);
        _.mb.subscribe(OO.EVENTS.PLAYED, 'wonder', _.onPlayed);
        _.mb.subscribe(OO.EVENTS.PAUSE, 'wonder', _.onPause);
        _.mb.subscribe(OO.EVENTS.PLAY, 'wonder', _.onPlay);
        _.mb.subscribe(OO.EVENTS.ERROR, 'wonder', _.onError);
        _.mb.subscribe(OO.EVENTS.PLAYER_EMBEDDED, 'wonder', _.hideLoader);

        requestAnimationFrame( _.Tick );

        window.wonderPlayer = this;
        window.wonder = _;
    };

    /*  Message bus event subscriber callbacks
    /* ======================================= */

    // Build the UI
    _.onPlayerCreate = function (event, elementId, params) {
        
        // Wrap the player element
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
        
        // Main buttons
        _.elements.playbutton = document.querySelector('.wonder-play');
        _.elements.bigplaybutton = document.querySelector('.wonder-play-big');
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
        _.elements.scrubber_vid = document.querySelector('.scrubber.vid');
        _.elements.scrubber_progress_vid = document.querySelector('.scrubber-progress.vid');
        _.elements.scrubber_handle_vid = document.querySelector('.scrubber-handle.vid');
        _.elements.scrubber_vol = document.querySelector('.scrubber.vol');
        _.elements.scrubber_progress_vol = document.querySelector('.scrubber-progress.vol');
        _.elements.scrubber_handle_vol = document.querySelector('.scrubber-handle.vol');

        // Listen for user interaction and show and hide the nav as necessary
        _.listen(_.elements.wrapper, 'mousemove', _.interaction);
        _.listen(_.elements.controls, 'mousemove', _.interaction);
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

        // Listen for interaction on the actual UI contols
        _.listen(_.elements.playbutton, 'click', _.play);
        _.listen(_.elements.bigplaybutton, 'click', _.play);
        _.listen(_.elements.pausebutton, 'click', _.pause);
        _.listen(_.elements.fullscreenbutton, 'click', _.fullscreen);
        _.listen(_.elements.volumebutton, 'click', _.volume);

        // Decide which listeners to use for the scrubbers.
        if ( _.isTouchDevice() ) {
            _.addClass(_.elements.controls, 'show');
            _.listen(_.elements.loader, 'touchend', _.toggleControls);
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
        }
    };

    // Update content, status and duration
    _.onContentReady = function (event, content) {

        _.info = content;
        _.elements.poster.getElementsByTagName('img')[0].src = content.promo || content.promo_image;
        _.elements.loader.className = '';
        _.elements.poster.getElementsByTagName('td')[0].innerHTML = (_.info.title.replace(/_/g,' '));
        _.removeClass( _.elements.poster, 'loading' );
        _.duration = content.duration/1000 || content.time;

        if ( document.getElementsByTagName('video').length > 0 ) {
            _.elements.video = document.getElementsByTagName('video')[0];
            _.listen( _.elements.video, 'loadedmetadata', function(e){
                // console.log('video meta data loaded');
            });
            _.listen( _.elements.video, 'webkitendfullscreen', function(e) {
                _.mb.publish(OO.EVENTS.PAUSE);
            });            
        }
    };
    
    // Event fired off by the OO message bus to indicate the playhead has moved.
    _.onTimeUpdate = function (event, time, duration, buffer, seekrange) {
        
        if ( time !== undefined ) {
            _.time = time;
        }

        _.loaded = true;
        if ( _.playing === true ) {
            _.hideLoader();
        }

        // if ( duration == NaN ) {
        //     _.duration = duration;
        // }

        // setTimeout( function(){    
        //    _.loaded = true;
        // }, 200 );

    };

    _.onError = function (error) {
        alert(JSON.stringify(error));
    };

    // Respond to the OO Message bus Play event
    _.onPlay = function () {
        if ( _.state.playing === false ) {
            _.addClass(_.elements.poster, 'hide');
            _.addClass(_.elements.playbutton, 'hidden');
            _.addClass(_.elements.bigplaybutton, 'hidden');
            _.removeClass(_.elements.pausebutton, 'hidden');
            _.state.playing = true;
        }

        setTimeout( function() {
            _.videoUpdate = true;
        }, 200);
    };
    
    // Respond to the OO Message bus Pause event
    _.onPause = function () {
        if ( _.state.playing === true ) {
            _.removeClass(_.elements.playbutton, 'hidden');
            _.removeClass(_.elements.bigplaybutton, 'hidden');
            _.addClass(_.elements.pausebutton, 'hidden');
            _.hideLoader();
            _.state.playing = false;
        }
    };

    _.onSeeked = function (e) {
        _.hideLoader();
        if ( _.played === false ) {
            _.mb.publish(OO.EVENTS.PLAY);    
        }
    };

    _.onVolumeChanged = function (e, vol) {
        _.newvolume = vol;
    };

    _.onPlayed = function (e) {
        _.state.playing = false;
        _.played = true;
        _.removeClass(_.elements.playbutton, 'hidden');
        _.addClass(_.elements.pausebutton, 'hidden');
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

    _.toggleControls = function (e) {
        _.prevent(e);

        if ( _.hasClass( _.elements.controls, 'show' ) ) {
            _.removeClass( _.elements.controls, 'show' );
            _.addClass( _.elements.controls, 'hide' );
        } else {
            _.removeClass( _.elements.controls, 'show' );
            _.addClass( _.elements.controls, 'show' );
        }
        
    };

    /*  UI listener callbacks
    /* ======================================= */

    _.play = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.played = false;
            _.mb.publish(OO.EVENTS.PLAY);    
        }
    };

    _.pause = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.mb.publish(OO.EVENTS.PAUSE);    
        }
    };

    _.volume = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {

            _.toggleClass( _.elements.scrubber_vol, 'vol-visible' );

            // if ( _.volume > 0 ) {
            //     _.mb.publish(OO.EVENTS.CHANGE_VOLUME,0);
            // } else {
            //     _.mb.publish(OO.EVENTS.CHANGE_VOLUME,1);
            // }    
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
        // _.elements.loader.className = 'show';
        _.mb.publish(OO.EVENTS.SEEK, seconds);
    };

    _.fullscreen = function (e) {
        _.prevent(e);
        if ( _.state.fullscreen === false ) {

            if ( _.ipad === true ) {
                _.elements.video.webkitEnterFullscreen();
                _.state.fullscreen = true;
            } else {
                _.mb.publish(OO.EVENTS.FULLSCREEN_CHANGED);
                _.attemptFullscreen(_.elements.wrapper);
                _.addClass(_.elements.wrapper, 'fullscreen');
                _.state.fullscreen = true;
            }

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
                console.log(_.newtime);
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
        _.scrubbed = true;
        _.mousetarget = 'vid';
        _.videoUpdate = false;
        _.pause();
        // _.mb.publish(OO.EVENTS.PLAY);
        _.newtime = (_.duration / 100) * percentage;
        _.videoPercentage = percentage;
    };

    _.scrubVol = function(percentage) {
        _.mousetarget = 'vol';
        _.mb.publish(OO.EVENTS.CHANGE_VOLUME, percentage/100);
    };

    _.showLoader = function () {
        clearTimeout( _.loaderTimeout );
        _.elements.loader.className = 'show';
    };

    _.hideLoader = function () {
        console.log('hide loader called ');
        window.clearTimeout( _.loaderTimeout );
        _.elements.loader.className = '';
    };

    // Show the controls
    _.showUI = function () {
        _.addClass( _.elements.controls, 'show' );
        _.removeClass( _.elements.controls, 'hide' );
    };

    // A user interaction has been detected, show the UI and 
    // set a timer to hide it again
    _.interaction = function () {
        _.showUI();
        window.clearTimeout( _.interactionTimeout );
        _.interactionTimeout = setTimeout( function() {
            _.addClass( _.elements.controls, 'hide' );
            _.removeClass( _.elements.controls, 'show' );
            _.removeClass( _.elements.scrubber_vol, 'vol-visible' );
        }, 1000 );
    };

    _.ActionTick = function () {

        if ( _.scrubbed === true ) {
            clearTimeout( _.videoTimeout );
            _.videoTimeout = setTimeout( function() {
                _.seek( _.newtime );    
                _.time = _.newtime;
            }, 100);

            _.scrubbed = false;
        }

    };

    _.UITick = function () {

        if ( _.scrubbed === true ) {
            _.elements.scrubber_progress_vid.style.width = _.videoPercentage + '%';
            _.elements.scrubber_handle_vid.style.left = _.videoPercentage + '%';
            _.showLoader();
        } else if ( _.mousetarget !== 'vid' && _.state.playing === true && _.videoUpdate === true ) {
            var percentage = ( (_.time/_.duration) * 100 ) + '%';        
            _.elements.scrubber_progress_vid.style.width = percentage;
            _.elements.scrubber_handle_vid.style.left = percentage;
        }

        // Check if the volume has changed
        if ( _.volume != _.newvolume ) {
            _.volume = _.newvolume;

            if ( _.newvolume === 0 ) {
                _.elements.volumebutton.className = 'volume wonder-volume vol-0';
            } else if ( _.newvolume > 0 && _.newvolume <= 0.33 ) {
                _.elements.volumebutton.className = 'volume wonder-volume vol-1';
            } else if ( _.newvolume > 0.33 && _.newvolume <= 0.65 ) {
                _.elements.volumebutton.className = 'volume wonder-volume vol-2';
            } else {
                _.elements.volumebutton.className = 'volume wonder-volume vol-3';
            }

            _.elements.scrubber_progress_vol.style.height = ( _.newvolume * 100 ) + '%';
            _.elements.scrubber_handle_vol.style.bottom = (( _.newvolume * 100 )-15) + '%';
        }

        // Update the time
        if ( _.state.playing === false ) {
            _.displayTime = _.getTime(_.duration);
        } else {    
            _.displayTime = _.getTime(_.time);
        }
        _.elements.timer.innerHTML = _.displayTime;

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

    _.BufferTick = function () {

        // Clear the timeout regardless
        clearTimeout( _.loaderTimeout );

        // If we are playing, set a timeout to show a loading message if this tick doesn't get called for a while.
        if ( _.state.playing === true ) {
            _.loaderTimeout = setTimeout( function() {
                if ( _.state.playing === true ) {
                    // _.elements.loader.className = 'show';
                    _.showLoader();
                }
            }, 650);
        }

    };

    _.Tick = function () {
        _.BufferTick();
        _.UITick();
        _.ActionTick();
        requestAnimationFrame( _.Tick );
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

    return _.WonderUIModule;
});