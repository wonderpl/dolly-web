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
					center: new google.maps.LatLng(51.518662, -0.207372),
					scrollwheel: false,
					navigationControl: false,
					mapTypeControl: false,
					scaleControl: false,
					draggable: false
				}

				scope.map = new google.maps.Map(elem[0], mapOptions);

				var marker = new google.maps.Marker({
					position: mapOptions.center,
					map: scope.map,
					title: 'Hello World!',
					icon: {
						url: '/static/assets/front/img/map-marker.png',
						origin: new google.maps.Point(0,0),
						anchor: new google.maps.Point(75,75),
						size: new google.maps.Size(150, 150)
					}
				});
			}
		}
	}]);


	app.directive('scrollAnchorLink', ['$timeout', function ($timeout) {
		return {
			priority: 100,
			restrict: 'C',
			link: function (scope, elem, attrs) {
				
				var target = d.getElementById('anchor-' + attrs.href.replace('#',''));

				if ( target !== null ) {

					elem.bind('click', function(e){
						e.preventDefault();

						var body = d.documentElement.scrollTop ? d.documentElement : d.body,
    						from = body.scrollTop,
    						to = target.getBoundingClientRect().top;

						scope.tween = new TWEEN.Tween( { y: from } )
			            .to( { y: to-75 }, 600 )
			            .easing( TWEEN.Easing.Cubic.Out )
			            .onUpdate( function () {
			            	body.scrollTop = this.y;
			            }).start();
					});
				} else {
					elem.bind('click', function(e){e.preventDefault();});
				}
			}
		}
	}]);


})(window,document,window.angular,'contentApp','directives');