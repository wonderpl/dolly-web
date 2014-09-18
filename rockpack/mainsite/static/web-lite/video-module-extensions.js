OO.plugin("WonderUIModuleExtensions", function (OO) {

  var extensions = function (mb, id) {

    this._mb = mb;
    this._id = id;

    this.filteredClass = 'filtered';
    this.filteredElements = [
      'wonder-play',
      'wonder-pause',
      'wonder-volume',
      'wonder-logo',
      'wonder-fullscreen',
      'scrubber-handle',
      'scrubber-progress',
      'wonder-timer'
    ];

    this.bindEvents();
  }

  extensions.prototype = {

    addClass : function (newClass) {
      this.className = this.className + ' ' + newClass;
    },

    removeClass : function(remove) {
        var newClassName = '';
        var i;
        var classes = this.className.split(' ');
        for(i = 0; i < classes.length; i++) {
            if(classes[i] !== remove) {
                newClassName += classes[i] + ' ';
            }
        }
        this.className = newClassName;
    },

    bindEvents : function () {
      // allow for WonderUIModule to load in OO.EVENTS.PLAYER_CREATED before initialising module
      this._mb.subscribe(OO.EVENTS.PLAYBACK_READY, 'wonder', this.init.bind(this));
      document.addEventListener('video-data-updated', this.onVideoDataChanged.bind(this));
    },

    onVideoDataChanged : function () {
      this.loadData();
      this.colorControls();
      this.hideLogo();
      this.showBuyButton();
      this.showDescriptionButton();
    },

    init : function () {
      this.loadData();
      this.createElements();
      this.applyFilterClass();
      this.colorControls();
      this.hideLogo();
      this.showBuyButton();
      this.showDescriptionButton();
      this.bindButtons();
    },

    loadData : function () {
      this.data = window.videoData;
    },

    createElements : function () {
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
    },

    applyFilterClass : function () {
      var elements = this.filteredElements;
      var l = elements.length;
      while (l--) {
        var elementToFilter = document.getElementsByClassName(elements[l])[0];
        this.addClass.call(elementToFilter, this.filteredClass);
      }
    },

    colorControls : function () {
      var rgb = JSON.parse(this.data.video.source_player_parameters.rgb);
      var svg = document.getElementById('ColourSvg');
      var red = document.querySelector('.red');
      var green = document.querySelector('.green');
      var blue = document.querySelector('.blue');
      red.setAttribute('slope', rgb.r/255);
      green.setAttribute('slope', rgb.g/255);
      blue.setAttribute('slope', rgb.b/255);
    },

    isOnlyWhiteSpaceContent : function (data) {
      var div = document.createElement('div');
      div.innerHTML = data;
      var content = div.textContent.replace(/\s/g, "").trim();
      return !!!content;
    },

    hideLogo : function () {
      var hideLogo = this.data.video.source_player_parameters.hideLogo === "True" ? true : false;
      var controls = document.getElementById('wonder-controls');
      if (controls) {
        if (hideLogo) {
            this.addClass.call(controls, 'no-logo');
        } else {
            this.removeClass.call(controls, 'no-logo');
        }
      }
    },

    showBuyButton : function () {
      var showBuyButton = this.data.video.source_player_parameters.showBuyButton === "True" ? true : false;
      var wrapper = document.getElementById('wonder-wrapper');
      var buyButton = document.getElementById('wonder-buy-button');
      if (wrapper && showBuyButton && this.data.video.link_title && this.data.video.link_url) {
        buyButton.innerHTML = this.data.video.link_title;
        buyButton.href = this.data.video.link_url;
        this.addClass.call(wrapper, 'show-buy-button');
      } else {
        this.removeClass.call(wrapper, 'show-buy-button');
      }
    },

    showDescriptionButton : function () {
      var showDescriptionButton = this.data.video.source_player_parameters.showDescriptionButton === "True" ? true : false;
      var wrapper = document.getElementById('wonder-wrapper');
      if (wrapper && showDescriptionButton && !this.isOnlyWhiteSpaceContent(videoData.video.description)) {
        this.addClass.call(wrapper, 'show-description-button');
      } else {
        this.removeClass.call(wrapper, 'show-description-button');
      }
    },

    bindButtons : function () {
      var descriptionButton = document.getElementById('wonder-description-button');
      var videoDescription = document.getElementById('wonder-video-description');
      var videoDescriptionContent = document.getElementById('wonder-video-description-content');
      var closeDescription = document.getElementById('wonder-video-description-close');
      descriptionButton.addEventListener('click', (function() {
        videoDescription.className = "active";
        videoDescriptionContent.innerHTML = this.data.video.description;
      }).bind(this), false);
      closeDescription.addEventListener('click', function() {
        videoDescription.className = "";
      }, false);
    }

  };

  return extensions;

});