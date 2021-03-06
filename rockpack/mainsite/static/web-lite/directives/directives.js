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
					var template, tmpl, div;
					elem.append('<div id="wonder-wrapper"><div id="youtube-player"></div></div>');
					template = $templateCache.get('player-ui.html');
					tmpl = $compile(template)(scope);
					div = d.getElementById('wonder-wrapper');
					var $div = ng.element(div);
					$div.append(tmpl);

					$timeout(function(){
						scope.player = new WonderYTModule('youtube-player', scope.vid.video.source_id, {
							autoplay: (!window.isMobileDevice() && (window.navigator.userAgent.toLowerCase().indexOf('ipad') === -1)) ? 1 : 0,
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
					if ( newValue !== '' && newValue !== undefined ) {

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
							elem.html('<iframe src="http://' + $location.$$host + ( $location.$$port !== 80 ? ':' + $location.$$port : '' ) + '/embed/' + scope.vid.id + '/?autoplay=1" width="100%" height="100%" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>');
							elem[0].getElementsByTagName('iframe')[0].contentWindow.focus();
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
				});

				elem.bind('error', function(e) {
					elem[0].src = '/static/assets/web-lite/img/thumbnail.jpg';
				});

				$timeout(function(){
					elem[0].src = attrs.src;
				}, 500);
			}
		}
	}]);


})(window,document,window.angular,'WebLite','directives');