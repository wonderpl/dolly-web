(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                       [ns + '.services'] /* module dependencies */);


	app.directive('googleMapsDirective', [ '$rootScope', '$timeout', function ($rootScope, $timeout) {
		return {
			priority: 100,
			restrict: 'C',
			link: function (scope, elem, attrs) {

				var buildMap = function() {
					var mapOptions = {
						zoom: 15,
						center: new google.maps.LatLng( attrs.lat, attrs.long ),
						scrollwheel: false,
						// navigationControl: false,
						// mapTypeControl: false,
						// scaleControl: false,
						draggable: false
					}

					scope.map = new google.maps.Map(elem[0], mapOptions);

					var marker = new google.maps.Marker({
						position: mapOptions.center,
						map: scope.map,
						title: 'Wonder PL Offices',
						icon: {
							url: '/static/assets/dolly/img/map-marker.png',
							origin: new google.maps.Point(0,0),
							anchor: new google.maps.Point(75,75),
							size: new google.maps.Size(150, 150)
						}
					});	
				}

				if ( $rootScope.mapsLoaded === true ) {
					$timeout(buildMap);
				}

				$rootScope.$watch('mapsLoaded', function(newValue, oldValue){
					if ( newValue === true ){
						$timeout(buildMap);
					}
				});
				
			}
		}
	}]);


	app.directive('scrollAnchorLink', ['$timeout', '$rootScope', 'scrollManager', 'windowSize', function ($timeout, $rootScope, scrollManager, windowSize) {
		return {
			priority: 100,
			restrict: 'C',
			link: function (scope, elem, attrs) {
				
				var target = d.getElementById( 'anchor-' + attrs.href.replace('#','') );
				if ( target !== null ) {

					elem.bind('click', function(e){
						e.preventDefault();
						scrollManager.scrollTo( target, (windowSize.ww() < 768) ? (-70) : (-40) );
					});

				} else {
					elem.bind('click', function(e){e.preventDefault();});
				}
			}
		}
	}]);


	app.directive('footerLink', ['$timeout', '$rootScope', '$location', 'scrollManager', function($timeout, $rootScope, $location, scrollManager){
		return {
			priority: 100,
			restrict: 'C',
			link: function (scope, elem, attrs) {
				
				elem.bind('click', function(e) {
					if ( $location.path() === '/about-us' ) {
						e.preventDefault();
						scrollManager.scrollTo( d.getElementById('anchor-' + attrs.anchor) );
					} else {
						$rootScope.queueAnchor = attrs.anchor;	
					}
				});
				
			}
		}
	}]);

	app.directive('lazyload', [ '$rootScope', '$timeout', '$q', function($rootScope, $timeout, $q){
		return {
			priority: 100,
			restrict: 'A',
			link: function(scope, elem, attrs) {

				function loadscript() {
					var _promise = new $q.defer(),
						done = false;

					elem[0].async = true;
					elem[0].src = attrs.src;
					elem[0].onload = elem[0].onreadystatechange = function() {
						if ( !done && (!this.readyState || this.readyState == "loaded" || this.readyState == "complete") ) {
							done = true;
							elem[0].onload = elem[0].onreadystatechange = null;
							_promise.resolve();
						}
					};

					return _promise.promise;
				}

				$timeout(function(){

					loadscript().then(function(){

						if ( attrs.type === 'font' ) {
							try{
								Typekit.load();
							} catch(e){}
						}
					});

					elem[0].src = attrs.src;
				});

			}
		}
	}]);
	

})(window,document,window.angular,'contentApp','directives');