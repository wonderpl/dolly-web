(function(w,d,ng,ns,m) {

	'use strict';

	var app = ng.module(ns + '.' + m /* module name */,
		[ns + '.services'] /* module dependencies */);


	app.directive('webLitePlayer', ['$rootScope', '$timeout', '$location', '$templateCache', '$compile', '$q', '$interval', function($rootScope, $timeout, $location, $templateCache, $compile, $q, $interval){
		return {
			priority: 100,
			restrict: 'C',
			link: function( scope, elem, attrs ) {

				$rootScope.playerElem = elem;
				scope.YTReady = false; 
				
				window.onYouTubeIframeAPIReady = function () {
					window.YTReady = true;
				};

				scope.getYTReady = function () {
					var q = $q.defer();					

					scope.YTReadyCheck = $interval(function( count ){
						if ( window.YTReady === true ) {
							scope.YTReady = true;
							$interval.cancel(scope.YTReadyCheck);
							$timeout(function(){
								q.resolve();
							});
						}
					}, 60);

					return q.promise;
				};


				var newYTVideo = function() {
					var template, tmpl;
					elem.append('<div id="wonder-wrapper"><div id="youtube-player"></div></div>');
					template = $templateCache.get('player-ui.html');
					tmpl = $compile(template)(scope);
					ng.element(d.getElementById('wonder-wrapper')).append(tmpl);

					$timeout(function(){
						scope.player = new WonderYTModule('youtube-player', scope.vid.video.source_id, {
							autoplay: 0,
							showinfo: 0,
							modestbranding: true,
							wmode: "opaque",
							controls: 0,
							volume: 0,
							color: 'white',
							rel: 0,
							iv_load_policy: 3
						}, scope.vid);
					});
				}

				$rootScope.$watch( 'currentvideo', function( newValue ) {
					if ( newValue !== '' ) {

						if ( 'player' in scope ) {
							try {
								Conduit.pause();
						        delete window.ytplayer;
        						delete window.wonder;
								delete scope.player;
							} catch (e) {}
						}

						elem[0].innerHTML = '';

						$timeout(function() {
							$rootScope.$apply(function(){
								scope.vid = $rootScope.videos[$rootScope.currentvideo];
								newVideo();
							});
						});
					}
				});


				var newVideo = function () {
					switch ( scope.vid.video.source ) {
						case 'youtube':
							scope.getYTReady().then(function(){
								newYTVideo();
							});
							break;

						case 'ooyala':
							console.log( 'ooyala video initialised' );
							elem.html('<iframe src="http://' + $location.$$host + ( $location.$$port !== 80 ? ':' + $location.$$port : '' ) + '/embed/' + scope.vid.id + '/" width="100%" height="100%" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>');
							break;
					}
				};

			}
		}
	}]);

	app.directive('videoThumbnail', ['$timeout', function( $timeout ){
		return {
			restrict: 'C',
			link: function( scope, elem, attrs ) {

				elem.bind('load', function(e) {
					// console.log('loaded');
				});

				elem.bind('error', function(e) {
					// console.log('error');
					elem[0].src = '/static/assets/web-lite/img/thumbnail.jpg';
				});

				$timeout(function(){
					elem[0].src = attrs.src;
				}, 500);
			}
		}
	}]);


	// app.directive('channelDirective', ['$rootScope,' '$timeout', function($rootScope, $timeout){
	// 	return {
	// 		priority: 100,
	// 		restrict: 'C',
	// 		link: function( scope, elem, attrs ) {

	// 		}
	// 	}
	// }]);


})(window,document,window.angular,'WebLite','directives');