(function(w,d,ng,ns,m) {

	'use strict';

	var app = ng.module(ns + '.' + m /* module name */,
		[ns + '.services'] /* module dependencies */);


	app.directive('webLitePlayer', ['$rootScope', '$timeout', '$location', '$templateCache', '$compile', '$q', '$interval', function($rootScope, $timeout, $location, $templateCache, $compile, $q, $interval){
		return {
			priority: 100,
			restrict: 'C',
			link: function( scope, elem, attrs ) {

				console.log($location);

				$rootScope.playerElem = elem;
				scope.YTReady = false;
				scope.OOReady = false;
				
				window.onYouTubeIframeAPIReady = function () {
					window.YTReady = true;
				};

				OO.ready(function() {
					window.OOReady = true;
				});

				scope.getOOReady = function() {
					var q = $q.defer();					

					scope.OOReadyCheck = $interval(function( count ){
						if ( window.OOReady === true ) {
							scope.OOReady = true;
							$interval.cancel(scope.OOReadyCheck);
							$timeout(function(){
								q.resolve();
							});
						}

					}, 60);

					return q.promise;
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
						scope.player = new WonderYTModule('youtube-player', 'nMoVqveSem4', {
							autoplay: 0,
							showinfo: 0,
							modestbranding: true,
							wmode: "opaque",
							controls: 0,
							volume: 0,
							color: 'white',
							rel: 0,
							iv_load_policy: 3
						});
					});
				}

				var newOOVideo = function() {
					$timeout(function() {
						elem.append('<div id="ooyala-player"></div>');
						scope.player = OO.Player.create( 'ooyala-player', scope.vid.video.source_id, {
							flashParams: { hide: 'all' },
							wmode: 'opaque',
							autoplay: false,
							layout: 'chromeless'
						});
					});
				};


				$rootScope.$watch( 'currentvideo', function( newValue ) {
					if ( newValue !== '' ) {

						if ( 'player' in scope ) {
							try {
								scope.player.destroy();
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
							// scope.getOOReady().then(function(){
							// 	newOOVideo();
							// });
							// elem.append('<iframe src="//player.vimeo.com/video/85134959?color=ffffff" width="100%" height="100%" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>');
							console.log('here');
							console.log('<iframe src="http://' + $location.$$host + ( $location.$$port !== 80 ? ':' + $location.$$port : '' ) + '/embed/' + scope.vid.id + '/" width="100%" height="100%" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>');
							elem.append('<iframe src="http://' + $location.$$host + ( $location.$$port !== 80 ? ':' + $location.$$port : '' ) + '/embed/' + scope.vid.id + '/" width="100%" height="100%" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>');
							break;
					}
				};

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