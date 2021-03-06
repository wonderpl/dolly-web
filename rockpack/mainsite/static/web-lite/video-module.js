
/* ======================================= */
/*  Custom Wonder UI module for the Ooyala player
/*  Date: Thurs 9th January 2014
/* ======================================= */

OO.plugin("WonderUIModule", function (OO) {

    var _ = {
        data: window.videoData,

        // Status vars
        framecount: 0,
        newvolume: 1,
        currentvolume: 0,
        played: false,
        scrubbed: false,
        scrubbing: false,
        metadataloaded: false,
        fullscreenrequested: false,
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

    // This section contains the HTML content to be used as the UI
    // '<a href="#" class="rewind wonder-rewind icon-ccw"></a>' +
    // '<span class="f-thin f-uppercase"></span>' +
    // '<a class="wonder-play-big"></a>' +
    var wonder_template =
        '<div id="wonder-poster" class="loading">' +
            '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyNpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNS1jMDE0IDc5LjE1MTQ4MSwgMjAxMy8wMy8xMy0xMjowOToxNSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIChNYWNpbnRvc2gpIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOjNGRUU0MzZGNkVGMTExRTNBQ0EzQjkyRDVDNTJFOTJCIiB4bXBNTTpEb2N1bWVudElEPSJ4bXAuZGlkOjNGRUU0MzcwNkVGMTExRTNBQ0EzQjkyRDVDNTJFOTJCIj4gPHhtcE1NOkRlcml2ZWRGcm9tIHN0UmVmOmluc3RhbmNlSUQ9InhtcC5paWQ6M0ZFRTQzNkQ2RUYxMTFFM0FDQTNCOTJENUM1MkU5MkIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6M0ZFRTQzNkU2RUYxMTFFM0FDQTNCOTJENUM1MkU5MkIiLz4gPC9yZGY6RGVzY3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tldCBlbmQ9InIiPz62H+JlAAAARUlEQVR42uzPQREAAAgDINc/9Mzg14MGpO18EBERERERERERERERERERERERERERERERERERERERERERERERERGRixVgABLFlZ3XwPXxAAAAAElFTkSuQmCC" alt="" id="wonder-poster"/>' +
            // '<table width="100%" height="100%" cellpadding="0" cellspacing="0"><tr><td width="100%" height="100%" align="center" valign="middle"><span></span></td></tr></table>' +
        '</div>' +
        '<div id="wonder-loader" class="show f-sans f-uppercase"><span></span></div>' +
        '<div id="wonder-controls">' +
            '<a class="play wonder-play player-icon-play filtered"></a>' +
            '<a class="pause wonder-pause player-icon-pause hidden filtered"></a>' +
            '<a class="volume wonder-volume vol-3 filtered">' +
                '<img class="vol-1" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAoCAYAAABq13MpAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAGBJREFUeNrs17EJgFAMBND/HcZacC+ntLJyo5gRxEYO3sGVgVeEQGZVjbQsIzDQ0NDQ0NDQ0NDQ0Jnoq7unodfukbge55eh+eNju3XvNLTrAQ0NDQ0NDQ0NDQ39Lo8AAwCo8wyaUULIQwAAAABJRU5ErkJggg==" />' +
                '<img class="vol-2" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAoCAYAAABq13MpAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAATNJREFUeNrsmLFKA0EQhnOaQlKo4APEwkIQsRILX8BO0iZV0BfIS1ilsbC2UcFW0EJs1CdQLKxTBCs9bEzwcP2OXGBykOOu2lmYHz7YKRa+O2Z3joucc7XQslALMCZt0iZt0iZt0vPyBCewXnlnOsY9EbtJfqEPjbJ7I4/fHjGsiPoFDuBDc3tcwo+od+AWGprbI6UJz242Z5rbY5oleID9rE5gG941X3kjaItWqcNRCPf0AK5FfRjKcLkT642iA6lJeijWEayFIJ1/s0kI0rti/V00ZLRIL0JX1I/pCNEu3csO3zQXmidiSgcSMRHfoF60x6fsFlzlRvgY9jSP8S9YFfUfHMO55q+819wDtMoI+5a+h084hU24KbvRZ3sswzijUiL7a2rSJm3SJm3SJk3+BRgA8LFe4j8YonoAAAAASUVORK5CYII=" />' +
                '<img class="vol-3" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAoCAYAAABq13MpAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAbhJREFUeNrs2c8rRFEUB/B53qSYaRYyVopSimTBhJRZ2diJlLAQs1IWFkr5H6xYYKOslGKNJfm5YGespPGzEDUZmeb53rq3jjtvyu6dU3PqU+dMM/U16d33zjie54WkVUVIYAUdug/WISEpdAxScA7HMCjt36MHdmAfGjiHvoc767V+uISBkp9SV4+AuTAOGe9v5WHK7zMcQhsxWLGCF/QfxDa0MQHfJLjqu+l7HKaHi7qKbIOr51togRznw2UXFsjcCPNmcBgf4w7s6auJqiw0wwPnY1x9m7OQ13ME5iTce1zDFpknISzhhmmV9LWQlBD6CJ7JLCJ0AU7InJByP31F+lYpoZ9IH5cS+oP0USmhq0j/KSV0PenfpIRuI/2NhNAqY5LMFxJCq8B1ZD6QEHqG9C9wyD10OwyTeQN+ON9Pu/r4NoucL2iCR87f9KK1eVpSgbmsEPyM6idxU2mo5vw0ntI7D1NZ6OC6QojCms/CZojj3qMSpn02TDkY47hh6oJXr7gy9oKGCvrqEYca6wlcLWk64VTCqlftp3thxHomLKpwwEHfYRk24ezfW5zyD0Xl0KXrV4ABABBpntz13cW2AAAAAElFTkSuQmCC" />' +
            '</a>' +
            '<a class="wonder-logo filtered" href="/" target="_blank"></a>' +
            '<a class="fullscreen wonder-fullscreen player-icon-fullscreen filtered"></a>' +
            '<span class="wonder-timer filtered">--:--</span>' +
            '<div class="scrubber vid loading">' +
                '<div class="scrubber-progress vid filtered"></div>' +
                '<div class="scrubber-buffer"></div>' +
                '<a class="scrubber-handle vid player-icon-circle filtered"></a>' +
                '<span class="scrubber-timer"></span>' +
            '</div>' +
            '<div class="scrubber-target vid">' +
                '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyNpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNS1jMDE0IDc5LjE1MTQ4MSwgMjAxMy8wMy8xMy0xMjowOToxNSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIChNYWNpbnRvc2gpIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOjNGRUU0MzZGNkVGMTExRTNBQ0EzQjkyRDVDNTJFOTJCIiB4bXBNTTpEb2N1bWVudElEPSJ4bXAuZGlkOjNGRUU0MzcwNkVGMTExRTNBQ0EzQjkyRDVDNTJFOTJCIj4gPHhtcE1NOkRlcml2ZWRGcm9tIHN0UmVmOmluc3RhbmNlSUQ9InhtcC5paWQ6M0ZFRTQzNkQ2RUYxMTFFM0FDQTNCOTJENUM1MkU5MkIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6M0ZFRTQzNkU2RUYxMTFFM0FDQTNCOTJENUM1MkU5MkIiLz4gPC9yZGY6RGVzY3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tldCBlbmQ9InIiPz62H+JlAAAARUlEQVR42uzPQREAAAgDINc/9Mzg14MGpO18EBERERERERERERERERERERERERERERERERERERERERERERERERGRixVgABLFlZ3XwPXxAAAAAElFTkSuQmCC" class="scrubber-trans vid" width="100%" height="100%" />' +
            '</div>' +
            '<div class="scrubber vol">' +
                '<div class="scrubber-progress vol filtered"></div>' +
                '<a class="scrubber-handle vol player-icon-circle filtered"></a>' +
            '</div>' +
            '<div class="scrubber-target vol">' +
                '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAyNpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNS1jMDE0IDc5LjE1MTQ4MSwgMjAxMy8wMy8xMy0xMjowOToxNSAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIChNYWNpbnRvc2gpIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOjNGRUU0MzZGNkVGMTExRTNBQ0EzQjkyRDVDNTJFOTJCIiB4bXBNTTpEb2N1bWVudElEPSJ4bXAuZGlkOjNGRUU0MzcwNkVGMTExRTNBQ0EzQjkyRDVDNTJFOTJCIj4gPHhtcE1NOkRlcml2ZWRGcm9tIHN0UmVmOmluc3RhbmNlSUQ9InhtcC5paWQ6M0ZFRTQzNkQ2RUYxMTFFM0FDQTNCOTJENUM1MkU5MkIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6M0ZFRTQzNkU2RUYxMTFFM0FDQTNCOTJENUM1MkU5MkIiLz4gPC9yZGY6RGVzY3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tldCBlbmQ9InIiPz62H+JlAAAARUlEQVR42uzPQREAAAgDINc/9Mzg14MGpO18EBERERERERERERERERERERERERERERERERERERERERERERERERGRixVgABLFlZ3XwPXxAAAAAElFTkSuQmCC" class="scrubber-trans vol" width="100%" height="100%" />' +
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

        _.ie8 = ( _.hasClass(document.querySelector('html'), 'lte9') ) ? true : false;
        _.ie10 = ( _.UA.indexOf('msie 1') !== -1 ) ? true : false;
        _.ipad = ( _.UA.indexOf('ipad') !== -1 ) ? true : false;
        _.ios = ( _.UA.indexOf('ipad') !== -1 || _.UA.indexOf('iphone') !== -1 ) ? true : false;
        _.ios5 = /(iphone|ipad).*os 5_.*/i.test(_.UA);
        _.isMobile = _.isMobileDevice();

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
        _.mb.subscribe(OO.EVENTS.PLAYBACK_READY, 'wonder', _.autoPlay);

        _.applySettings();
    };

    _.applySettings = function () {

      _.showControls = !!(_.getQuery('controls'));
    };

    //
    // Romeo integration
    //
    _.initRomeoIntegration = function () {
        _.filteredClass = 'filtered';
        _.filteredElements = [
            'wonder-play',
            'wonder-pause',
            'wonder-volume',
            'wonder-logo',
            'wonder-fullscreen',
            'scrubber-handle',
            'scrubber-progress',
            'wonder-timer'
        ];

        _.createElements();
        _.applyFilterClass();
        _.onVideoDataChanged();
        _.bindButtons();
        document.addEventListener('video-data-updated', _.onVideoDataChanged);
    };

    _.onVideoDataChanged = function () {
        _.colorControls();
        _.hideLogo();
        _.showBuyButton();
        _.showDescriptionButton();
    };

    _.createElements = function () {
        var svg = '<svg xmlns="http://www.w3.org/2000/svg" style="height: 0; width: 0;" id="ColourSvg"><filter id="ColourFilter" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncR class="brightness red" type="linear" slope="1"/><feFuncG class="brightness green" type="linear" slope="1"/><feFuncB class="brightness blue" type="linear" slope="1"/></feComponentTransfer></filter></svg>';
        var style = '<style id="ColourStyle">.filtered { -webkit-filter : url("#ColourFilter"); -webkit-transform: translate3d(0px,0px,0px); -webkit-backface-visibility: hidden; -webkit-perspective: 1000; }</style>';
        var buyButton = '<a id="wonder-buy-button" class="btn video-overlay-button video-buy-button js-video-buy" target="_top">Buy</a>';
        var descriptionButton = '<a id="wonder-description-button" class="btn video-overlay-button video-description-button js-video-description">Description</a>';
        var description = '<div id="wonder-video-description"><div id="wonder-video-description-close">x</div><div id="wonder-video-description-content"></div></div>';
        var poster = document.getElementById('wonder-poster');
        poster.insertAdjacentHTML('beforebegin', buyButton);
        poster.insertAdjacentHTML('beforebegin', descriptionButton);
        poster.insertAdjacentHTML('beforebegin', description);
        document.body.insertAdjacentHTML('beforeend', svg);
        document.head.insertAdjacentHTML('beforeend', style);
    };

    _.applyFilterClass = function () {
        var elements = this.filteredElements;
        var l = elements.length;
        while (l--) {
            var elementToFilter = document.getElementsByClassName(elements[l])[0];
            _.addClass(elementToFilter, _.filteredClass);
        }
    };

    _.colorControls = function () {
      var rgb = { r: 255, g: 255, b: 255 };
      if (_.data.video && _.data.video.source_player_parameters && _.data.video.source_player_parameters.rgb)
        rgb = JSON.parse(_.data.video.source_player_parameters.rgb);
      var svg = document.getElementById('ColourSvg');
      var red = document.querySelector('.red');
      var green = document.querySelector('.green');
      var blue = document.querySelector('.blue');
      red.setAttribute('slope', rgb.r/255);
      green.setAttribute('slope', rgb.g/255);
      blue.setAttribute('slope', rgb.b/255);
    };

    _.hideLogo = function () {
        var hideLogo = false;
        if (_.data.video && _.data.video.source_player_parameters && _.data.video.source_player_parameters.hideLogo)
            hideLogo = (_.data.video.source_player_parameters.hideLogo === "True");
        var controls = document.getElementById('wonder-controls');
        if (controls) {
            if (hideLogo) {
                _.addClass(controls, 'no-logo');
            } else {
                _.removeClass(controls, 'no-logo');
            }
        }
    };

    _.showBuyButton = function () {
        var buyButton = document.getElementById('wonder-buy-button');
        if (buyButton && _.data.video.link_title && _.data.video.link_url) {
            buyButton.innerHTML = _.data.video.link_title;
            buyButton.href = _.data.video.link_url;
            _.elements.buyButton = buyButton;
            if ( _.hasClass( _.elements.controls, 'show' ) ) {
                _.removeClass(buyButton, 'hide');
                _.addClass(buyButton, 'show');
            }
            else {
                _.removeClass(buyButton, 'show');
                _.addClass(buyButton, 'hide');
            }
        }
        else {
            _.removeClass(buyButton, 'show');
            _.addClass(buyButton, 'hide');
            _.elements.buyButton = void(0);
        }
    };

    _.showDescriptionButton = function () {
        var descriptionButton = document.getElementById('wonder-description-button');
        if (descriptionButton && !_.isOnlyWhiteSpaceContent(_.data.video.description)) {
            _.elements.descriptionButton = descriptionButton;
            if ( _.hasClass( _.elements.controls, 'show' ) ) {
                _.removeClass(descriptionButton, 'hide');
                _.addClass(descriptionButton, 'show');
            }
            else {
                _.removeClass(descriptionButton, 'show');
                _.addClass(descriptionButton, 'hide');
            }
        } else {
            _.removeClass(descriptionButton, 'show');
            _.addClass(descriptionButton, 'hide');
            _.elements.descriptionButton = void(0);
        }
    };

    _.isOnlyWhiteSpaceContent = function (data) {
        var div = document.createElement('div');
        div.innerHTML = data;
        var content = div.textContent.replace(/\s/g, "").trim();
        return !content;
    };

    _.bindButtons = function () {
        var descriptionButton = document.getElementById('wonder-description-button');
        var videoDescription = document.getElementById('wonder-video-description');
        var videoDescriptionContent = document.getElementById('wonder-video-description-content');
        var closeDescription = document.getElementById('wonder-video-description-close');
        descriptionButton.addEventListener('click', (function() {
            videoDescription.className = "active";
            videoDescriptionContent.innerHTML = _.data.video.description;
        }), false);
        closeDescription.addEventListener('click', function() {
            videoDescription.className = "";
        }, false);
    };

    //  Message bus event subscriber callbacks
    // =======================================

    // Build the UI
    _.onPlayerCreate = function (event, elementId, params) {

        // Wrap the player element
        _.wrapper = document.createElement('div');
        _.wrapper.setAttribute('id', 'wonder-wrapper');
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
        _.elements.scrubber_buffer = document.querySelector('.scrubber-buffer');
        _.elements.scrubber_progress_vid = document.querySelector('.scrubber-progress.vid');
        _.elements.scrubber_handle_vid = document.querySelector('.scrubber-handle.vid');
        _.elements.scrubber_vol = document.querySelector('.scrubber.vol');
        _.elements.scrubber_target_vol = document.querySelector('.scrubber-target.vol');
        _.elements.scrubber_progress_vol = document.querySelector('.scrubber-progress.vol');
        _.elements.scrubber_handle_vol = document.querySelector('.scrubber-handle.vol');
        _.elements.scrubber_timer = document.querySelector('.scrubber-timer');

        // Listen for user interaction and show and hide the nav as necessary
        if ( _.isTouchDevice() === false ) {
            _.listen(_.elements.wrapper, 'mousemove', _.interaction);
            _.listen(_.elements.controls, 'mousemove', _.interaction);
            _.listen(_.elements.poster, 'mousemove', _.interaction);
            _.listen(_.elements.loader, 'mousemove', _.interaction);
            _.listen(_.elements.playbutton, 'mousemove', _.interaction);
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

        // Prevent window scroll
        window.onkeydown = function(e) {
            if ( e.keyCode == 32 ) {
                _.togglePlay();
            }
            return (e.keyCode !== 32);
        };

        if ( !_.ie8 ) {
            document.addEventListener("fullscreenchange", function () {
                if ( document.fullscreen === false ) {
                    _.state.fullscreen = false;
                }
            }, false);

            document.addEventListener("mozfullscreenchange", function () {
                if ( document.mozFullScreen === false ) {
                    _.state.fullscreen = false;
                }
            }, false);

            document.addEventListener("webkitfullscreenchange", function () {
                if ( document.webkitIsFullScreen === false ) {
                    _.state.fullscreen = false;
                }
            }, false);

            document.addEventListener("msfullscreenchange", function () {
                if ( document.msFullscreenElement === false ) {
                    _.state.fullscreen = false;
                }
            }, false);
        }

        // Listen for interaction on the actual UI contols
        _.listen(_.elements.playbutton, 'click', _.play);
        _.listen(_.elements.pausebutton, 'click', _.pause);
        _.listen(_.elements.fullscreenbutton, 'click', _.fullscreen);
        _.listen(_.elements.fullscreenbutton, 'touchend', _.fullscreen);
        _.listen(_.elements.volumebutton, 'click', _.volume);


        // Custom events
        _.listen(_.elements.wrapper, 'restart', _.restart);

        _.listen(document, 'video-data-change', _.applyChanges);

        if ( _.showControls ) {
          _.addClass(_.elements.controls, 'show');
          if (_.elements.descriptionButton)
            _.addClass(_.elements.descriptionButton, 'show');
          if (_.elements.buyButton)
            _.addClass(_.elements.buyButton, 'show');
        }

        // Decide which listeners to use for the scrubbers.
        if ( _.isTouchDevice() ) {
            _.addClass(_.elements.controls, 'show');
            if (_.elements.descriptionButton)
                _.addClass(_.elements.descriptionButton, 'show');
            if (_.elements.buyButton)
                _.addClass(_.elements.buyButton, 'show');
            _.listen(_.elements.loader, 'click', _.toggleControls);
            if ( _.ios5 === false ) {
                _.listen(_.elements.scrubber_trans, 'touchstart', _.touchDown);
                _.listen(_.elements.scrubber_trans, 'touchmove', _.scrubTouch);
                _.listen(_.elements.scrubber_trans, 'touchleave', _.scrubUp);
            } else {
                _.listen(_.elements.scrubber_trans[0], 'touchstart', _.mouseDown);
                _.listen(_.elements.scrubber_trans[0], 'touchmove', _.scrubTouch);
                _.listen(_.elements.scrubber_trans[0], 'touchleave', _.scrubUp);
            }
        } else {
            _.listen(_.elements.loader, 'click', _.togglePlay);
            _.listen(_.elements.scrubber_trans, 'mousedown', _.mouseDown);
            _.listen(_.elements.scrubber_trans, 'mousemove', _.scrubMouse);
            _.listen(_.elements.scrubber_trans, 'mouseup', _.scrubUp);
            _.listen(_.elements.loader, 'mousemove', function(){
                _.controlshovered = false;
            });
            _.listen(_.elements.controls, 'mouseleave', function(){
                _.controlshovered = false;
            });
            _.listen(_.elements.controls, 'mouseout', function(){
                _.controlshovered = false;
            });
            _.listen(_.elements.controls, 'mouseenter', function(){
                _.controlshovered = true;
            });
        }

        if ( _.ios === true ) {
            _.addClass( _.elements.controls, 'volume-disabled' );
        }

        if ( _.ios5 === true ) {
            _.addClass( _.elements.poster, 'ios5' );
        }

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

        Conduit.setFPS(25);
        Conduit.start();

        // _.elements.poster.getElementsByTagName('span')[0].innerHTML = (_.data.title.replace(/_/g,' '));
        _.duration = _.data.video.duration;
    };

    // Update content, status and duration
    _.onContentReady = function (event, content) {

        _.info = content;

        if (_.data.video.thumbnail_url)
            _.elements.poster.getElementsByTagName('img')[0].src = _.data.video.thumbnail_url;

        _.hideLoader();

        if ( _.ie10 ) {
            _.addClass( _.elements.controls, 'ie10' );
        }

        _.elements.loader.getElementsByTagName('span')[0].innerHTML = '';
        setTimeout( function(){
            _.removeClass( _.elements.poster, 'loading' );
        }, 600);

        _.flash = ( _.elements.wrapper.getElementsByTagName('object')[0] !== undefined );

        if ( document.getElementsByTagName('video').length > 0 ) {
            _.elements.video = document.getElementsByTagName('video')[0];
            _.listen( _.elements.video, 'loadedmetadata', function(e){
                _.metadataloaded = true;
                if ( _.fullscreenrequested === true ) {
                    _.fullscreen();
                }
            });
            _.listen( _.elements.video, 'webkitendfullscreen', function(e) {
                _.mb.publish(OO.EVENTS.PAUSE);
            });
        }

        _.loaded = true;
    };

    _.autoPlay = function() {

      // user setting
      var autoplaySetting = (parseInt(_.data.video.loop, 10) === 1);

      var autoplayQueryString = _.getQuery( 'autoplay' );

      var autoplayQueryStringParsed = parseInt(autoplayQueryString, 10);

      var autoplayQueryStringValue = isNaN(autoplayQueryStringParsed) ? null : autoplayQueryStringParsed;

      // query string value is true or false or not set
      autoplayQueryStringValue = autoplayQueryStringValue === null ? null : !!autoplayQueryStringValue;

      // use query string if set
      var autoplay = autoplayQueryStringValue === null ? autoplaySetting : autoplayQueryStringValue;

      var autoplaySuitable = (_.isMobile === false && _.ipad === false);

      if ( autoplay && autoplaySuitable ) {
        setTimeout( function() {
          _.loaded = true;
          _.controlshovered = false;
          _.played = false;
          _.mb.publish(OO.EVENTS.PLAY);
        }, 200);
      }

      // Start romeo integration
      _.initRomeoIntegration();
    };

    // Event fired off by the OO message bus to indicate the playhead has moved.
    _.onTimeUpdate = function (event, time, duration, buffer, seekrange) {

        _.buffer = buffer;

        if ( _.scrubbed === true ) {
            setTimeout( function() {
                _.scrubbed = false;
            }, 300);
        }

        if ( time !== undefined ) {
            _.time = time;
        }

        if ( time !== 0 && time !== undefined && _.scrubbed === false) {
            _.timers.buffer = 0;
            _.hideLoader();
        }

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
            _.removeClass(_.elements.pausebutton, 'hidden');
            _.timers.interaction = 0;
        }
        _.hideLoader();
        _.state.playing = true;
    };

    // Respond to the OO Message bus Pause event
    _.onPause = function () {
        if ( _.state.playing === true ) {
            _.removeClass(_.elements.playbutton, 'hidden');
            _.addClass(_.elements.pausebutton, 'hidden');
            _.hideLoader();
            _.state.playing = false;
            _.controlshovered = true;
        }
    };

    _.onSeeked = function (e) {
        if ( _.played === false ) {
            _.mb.publish(OO.EVENTS.PLAY);
        }
    };

    _.onVolumeChanged = function (e, vol) {
        _.newvolume = vol;
    };

    _.onPlayed = function (e) {
        var loopVideo = (parseInt(_.data.video.loop, 10) === 1);
        if ( loopVideo && _.isMobile === false && _.ipad === false ) {
          _.mb.publish(OO.EVENTS.PLAY);
        } else {
          _.state.playing = false;
          _.played = true;
          _.removeClass(_.elements.playbutton, 'hidden');
          _.addClass(_.elements.pausebutton, 'hidden');
          _.removeClass( _.elements.poster, 'hide' );
          _.hideLoader();
        }
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
            _.addClass( _.elements.loader, 'no-cursor');

            if (_.elements.descriptionButton) {
                _.removeClass(_.elements.descriptionButton, 'show');
                _.addClass(_.elements.descriptionButton, 'hide');
            }
            if (_.elements.buyButton) {
                _.removeClass(_.elements.buyButton, 'show');
                _.addClass(_.elements.buyButton, 'hide');
            }
            return;
        } else {
            _.removeClass( _.elements.controls, 'hide' );
            _.addClass( _.elements.controls, 'show' );

            if (_.elements.descriptionButton) {
                _.removeClass(_.elements.descriptionButton, 'hide');
                _.addClass(_.elements.descriptionButton, 'show');
            }
            if (_.elements.buyButton) {
                _.removeClass(_.elements.buyButton, 'hide');
                _.addClass(_.elements.buyButton, 'show');
            }
            _.removeClass( _.elements.loader, 'no-cursor');
            return;
        }
    };

    // http://stackoverflow.com/a/6842900
    _.updateData = function setToValue(obj, value, path) {
        path = path.split('.');
        var parent = obj;
        for (var i = 0; i < path.length -1; i += 1) {
            parent = parent[path[i]];
        }
        parent[path[path.length-1]] = value;
    };


    _.applyChanges = function (e) {
      _.updateData(_.data, e.detail.data, e.detail.path);
      document.dispatchEvent(new CustomEvent('video-data-updated'));
    };

    /*  UI listener callbacks
    /* ======================================= */

    _.play = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.controlshovered = true;
            _.played = false;
            _.mb.publish(OO.EVENTS.PLAY);
        }
    };

    _.pause = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.controlshovered = true;
            _.mb.publish(OO.EVENTS.PAUSE);
        }
    };

    _.volume = function (e) {
        _.prevent(e);
        if ( _.loaded === true ) {
            _.toggleClass( _.elements.scrubber_vol, 'vol-visible' );
            _.toggleClass( _.elements.scrubber_target_vol, 'vol-visible' );
        }
    };

    _.stop = function (e) {
      _.prevent(e);
      _.mb.publish(OO.EVENTS.SEEK, 0);
      window.setTimeout(function () {
        _.mb.publish(OO.EVENTS.PAUSE);
      }, 1000);
    };

    _.restart = function (e) {
      _.prevent(e);
      if ( _.loaded === true ) {
        _.stop();
        window.setTimeout(function () {
          _.state.playing === false;
          _.removeClass(_.elements.poster, 'hide');
          _.removeClass(_.elements.playbutton, 'hidden');
          _.addClass(_.elements.pausebutton, 'hidden');
          _.timers.interaction = 0;
        }, 1000);
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

    // _.spacebarPressed = function(e) {
    //     if ( e.keyCode === 32 ) {
    //         _.togglePlay();
    //     }
    // };

    _.seek = function (seconds) {
        _.mb.publish(OO.EVENTS.SEEK, seconds);
    };

    _.fullscreen = function (e) {
        _.prevent(e);

        if ( _.ipad === true ) {

            if ( _.metadataloaded === false ) {
                _.elements.video.play();
                _.fullscreenrequested = true;
                _.onPlay();
            } else if ( _.elements.video.webkitDisplayingFullscreen === false ) {
                _.elements.video.webkitEnterFullscreen();
                _.addClass(_.elements.wrapper, 'fullscreen');
                _.state.fullscreen = true;
            } else {
                document.webkitExitFullscreen();
                _.removeClass(_.elements.wrapper, 'fullscreen');
                _.state.fullscreen = false;
            }
        } else {
            if ( _.state.fullscreen === false ) {
                _.mb.publish(OO.EVENTS.FULLSCREEN_CHANGED);
                _.attemptFullscreen(_.elements.wrapper);
                _.addClass(_.elements.wrapper, 'fullscreen');
                _.state.fullscreen = true;
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
        }
    };

    // The scrubber has been clicked on
    _.mouseDown = function(e) {
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

    _.touchDown = function(e) {
        _.prevent(e);
        if ( _.loaded === true ) {

            if ( _.mousetarget === 'vid' ) {
                _.play();
            }
            _.mousedown = true;
            _.scrubTouch(e);
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
        _.mb.publish(OO.EVENTS.CHANGE_VOLUME, percentage/100);
    };

    _.showLoader = function () {
        _.addClass( _.elements.scrubber_vid, 'loading' );
        _.addClass( _.elements.scrubber_buffer, 'hide' );
        _.addClass( _.elements.scrubber_timer, 'show' );
        _.addClass( _.elements.loader, 'show' );
    };

    _.hideLoader = function () {
        _.removeClass( _.elements.scrubber_vid, 'loading' );
        _.removeClass( _.elements.scrubber_buffer, 'hide' );
        _.removeClass( _.elements.scrubber_timer, 'show' );
        _.removeClass( _.elements.loader, 'show' );
    };

    // Show the controls
    _.showUI = function () {
        _.addClass( _.elements.controls, 'show' );

        if (_.elements.descriptionButton) {
            _.removeClass(_.elements.descriptionButton, 'hide');
            _.addClass(_.elements.descriptionButton, 'show');
        }
        if (_.elements.buyButton) {
            _.removeClass(_.elements.buyButton, 'hide');
            _.addClass(_.elements.buyButton, 'show');
        }
        _.removeClass( _.elements.controls, 'hide' );
        _.removeClass( _.elements.loader, 'no-cursor');
    };

    _.hideUI = function () {
        _.addClass( _.elements.controls, 'hide' );
        _.removeClass( _.elements.controls, 'show' );
        _.removeClass( _.elements.scrubber_vol, 'vol-visible' );
        _.removeClass( _.elements.scrubber_target_vol, 'vol-visible' );
        _.addClass( _.elements.loader, 'no-cursor');
        if (_.elements.descriptionButton) {
            _.removeClass(_.elements.descriptionButton, 'show');
            _.addClass(_.elements.descriptionButton, 'hide');
        }
        if (_.elements.buyButton) {
            _.removeClass(_.elements.buyButton, 'show');
            _.addClass(_.elements.buyButton, 'hide');
        }
    };

    // A user interaction has been detected, show the UI and
    // set a timer to hide it again
    _.interaction = function (e) {
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

      // console.log('_.loaded : ', _.loaded);
      // console.log('_.time : ', _.time);
      // console.log('_.scrubbed', _.scrubbed);
      // console.log('_.timers.seek', _.timers.seek);

        if ( _.scrubbed === true ) {
            _.elements.scrubber_progress_vid.style.width = _.videoPercentage + '%';
            _.elements.scrubber_handle_vid.style.left = _.videoPercentage + '%';
            _.elements.scrubber_timer.style.left = _.videoPercentage + '%';
            _.elements.scrubber_timer.innerHTML = _.getTime( _.newtime );
            _.showLoader();
        } else if ( _.loaded === true && _.time !== undefined && _.scrubbed === false && _.timers.seek > 60 ) {

            var percentage = ( (_.time/_.duration) * 100 ) + '%';

            // console.log(_.time);
            // console.log(_.duration);

            // console.log(percentage);

            _.elements.scrubber_progress_vid.style.width = percentage;
            _.elements.scrubber_handle_vid.style.left = percentage;
            _.elements.scrubber_timer.style.left = percentage;
            _.elements.scrubber_timer.innerHTML = _.getTime( _.time );
        }

        // Check if the volume has changed
        if ( _.currentvolume != _.newvolume ) {
            _.currentvolume = _.newvolume;

            if ( _.newvolume === 0 ) {
                _.elements.volumebutton.className = 'filtered volume wonder-volume vol-0';
            } else if ( _.newvolume > 0 && _.newvolume <= 0.33 ) {
                _.elements.volumebutton.className = 'filtered volume wonder-volume vol-1';
            } else if ( _.newvolume > 0.33 && _.newvolume <= 0.65 ) {
                _.elements.volumebutton.className = 'filtered volume wonder-volume vol-2';
            } else {
                _.elements.volumebutton.className = 'filtered volume wonder-volume vol-3';
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

        if ( _.timers.interaction === 40 ) {
            if ( _.isTouchDevice() === false && _.controlshovered === false && _.showControls === false) {
                _.hideUI();
            }
        }
    };

    _.bufferTick = function () {
        if ( _.state.playing === true ) {
            _.timers.buffer++;
        }
        if ( _.timers.buffer === 30 ) {
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


    /*  Utility Functions
    /* ======================================= */

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

    _.getQuery = function (name) {
        name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
        var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
            results = regex.exec(location.search);
        return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
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
        // || 'onmsgesturechange' in window
        return 'ontouchstart' in window;
    };

    _.isMobileDevice = function () {
        var check = true;
        (function(a){if(/(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(a)||/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(a.substr(0,4)))check = false})(navigator.userAgent||navigator.vendor||window.opera);
        return !check;
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

    return _.WonderUIModule;
});
