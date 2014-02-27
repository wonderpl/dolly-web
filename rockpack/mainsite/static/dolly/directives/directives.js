(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                       [ns + '.services'] /* module dependencies */);


	app.directive('googleMapsDirective', ['$timeout', function ($timeout) {
		return {
			priority: 100,
			restrict: 'C',
			link: function (scope, elem, attrs) {

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
		}
	}]);


	app.directive('scrollAnchorLink', ['$timeout', '$rootScope', 'scrollManager', function ($timeout, $rootScope, scrollManager) {
		return {
			priority: 100,
			restrict: 'C',
			link: function (scope, elem, attrs) {
				
				var target = d.getElementById( 'anchor-' + attrs.href.replace('#','') );
				if ( target !== null ) {

					elem.bind('click', function(e){
						e.preventDefault();
						scrollManager.scrollTo( target );
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
	

})(window,document,window.angular,'contentApp','directives');