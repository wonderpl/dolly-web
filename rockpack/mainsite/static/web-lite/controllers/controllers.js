(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
        [ns + '.services',
        ns + '.directives'] /* module dependencies */);

    app.controller('WebLiteCtrl', ['$scope', '$timeout','$location', '$rootScope', '$templateCache', '$sanitize', '$compile', '$http', 'querystring', 'windowResizer', 'UserService', function($scope, $timeout, $location, $rootScope, $templateCache, $sanitize, $compile, $http, querystring, windowResizer, UserService) {

        $rootScope.weblite = true;
        $rootScope.assets_url = window.assets_url;
        $rootScope.selected_video = window.selected_video || false;
        $rootScope.channel_data = window.channel_data;
        $rootScope.owner = window.channel_data.owner;
        $rootScope.videos = Array.prototype.slice.call( $rootScope.channel_data.videos.items );
        $rootScope.api = window.apiUrls;
        $rootScope.shareurl = "";

        // shareuser is either the owner of the channel, or the user
        // represented by the shareuser query string.
        var shareuser = querystring.search('shareuser');
        if ( shareuser.length > 0 ) {
            UserService.fetchUser(shareuser);
        } else {
            $rootScope.user = $rootScope.owner;
        }

        if ( $rootScope.selected_video !== false ) {
            $rootScope.videos.push( $rootScope.selected_video );
            $timeout( function() {
                $rootScope.$apply(function(){
                    $rootScope.currentvideo = $rootScope.videos.length-1;
                    $rootScope.currentpage = 0;
                });
            });
        } else {
            $rootScope.currentvideo = 0;
            $rootScope.currentpage = 0;
        }

        $rootScope.$watch( 'currentvideo', function(newValue, oldValue) {
            if ( newValue !== undefined ) {
                $timeout( function() {
                    $rootScope.$apply(function() {
                        $rootScope.shareurl = ($location.$$protocol + '://' + $location.$$host + ( $location.$$port !== 80 ? ':' + $location.$$port : '' ) + '/channel/-/' + $rootScope.channel_data.id + '/?video=' +  $rootScope.videos[$rootScope.currentvideo].id);        
                        // console.log( $rootScope.videos[$rootScope.currentvideo] );
                        if ( $rootScope.videos[$rootScope.currentvideo].video.source === 'ooyala' ) {
                            $rootScope.embedurl = ($location.$$protocol + '://' + $location.$$host + ( $location.$$port !== 80 ? ':' + $location.$$port : '' ) + '/embed/' + $rootScope.videos[$rootScope.currentvideo].id);
                        } else {
                            $rootScope.embedurl = '//www.youtube.com/embed/' + $rootScope.videos[$rootScope.currentvideo].video.source_id;
                        }
                    });
                });                
            }
        });

    }]);    


    app.controller('PlayerCtrl', ['$scope', '$timeout','$location', '$rootScope', '$templateCache', '$sanitize', '$compile', '$http', function($scope, $timeout, $location, $rootScope, $templateCache, $sanitize, $compile, $http) {

        var $this = ng.element(d.getElementById('player')),
            template, 
            $scp, 
            tmpl;

        template = $templateCache.get('player.html');
        tmpl = $compile(template)($scope);
        $this.html('').append(tmpl);

        $scope.embedOptionsShowing = false;
        $scope.toggleEmbedOptions = function(event){
            if ( $scope.embedOptionsShowing === false ) {

                var body = d.documentElement.scrollTop ? d.documentElement : d.body,
                    from = body.scrollTop,
                    el = event.srcElement || event.target, 
                    target = el.getBoundingClientRect().top-12;

                $scope.tween = new TWEEN.Tween( { y: from } )
                .to( { y: target }, 600 )
                .easing( TWEEN.Easing.Cubic.Out )
                .onUpdate( function () {
                    body.scrollTop = this.y;
                }).start();

                $scope.embedOptionsShowing = true;
            } else {
                $scope.embedOptionsShowing = false;
            }
        };

        $scope.copyToClipboard = function(event) {
        };

        $scope.shareFacebook = function() {
            FB.ui({
                method: 'feed',
                link: $location.absUrl(),
                picture: $rootScope.videos[$rootScope.currentvideo].video.thumbnail_url,
                name: 'WonderPL',
                caption: 'Shared a video with you'
            });
        };

        $scope.shareTwitter = function() {
            // console.log( $location.$$protocol + '://' + $location.$$host + ( $location.$$port !== 80 ? ':' + $location.$$port : '' ) + '/channel/-/' + $rootScope.channel_data.id + '/?video=' +  $rootScope.videos[$rootScope.currentvideo].id );
            window.open("http://twitter.com/intent/tweet?url=" + $rootScope.shareurl);
        };


    }]);


    app.controller('ChannelCtrl', ['$scope', '$timeout','$location', '$rootScope', '$templateCache', '$sanitize', '$compile', 'windowSize', function($scope, $timeout, $location, $rootScope, $templateCache, $sanitize, $compile, windowSize ) {

        var $this = ng.element(d.getElementById('channel')),
            template, 
            $scp, 
            tmpl;

        $rootScope.wW = windowSize.ww();
        $scope.items = $rootScope.videos.length;
        $scope.touchDevice = 'ontouchstart' in window || 'onmsgesturechange' in window;

        ng.extend($scope, $rootScope.channel_data);
        template = $templateCache.get('channel.html');
        tmpl = $compile(template)($scope);
        $this.html('').append(tmpl);

        $scope.changeVideo = function(e, index) {
            e.preventDefault();

            // if ( $rootScope.videos[$rootScope.currentvideo].video.source === 'youtube' ) {
            //     try { 
            //         Conduit.pause();
            //         window.wonder.destroy();
            //     } catch (e) {}
                
            //     $timeout( function() {
            //         var body = d.documentElement.scrollTop ? d.documentElement : d.body,
            //             from = body.scrollTop, 
            //             target = from - Math.abs(d.querySelector('.avatar').getBoundingClientRect().top) - 20;

            //         $scope.tween = new TWEEN.Tween( { y: from } )
            //         .to( { y: target }, 600 )
            //         .easing( TWEEN.Easing.Cubic.Out )
            //         .onUpdate( function () {
            //             body.scrollTop = this.y;
            //         }).start();
                
            //         $rootScope.$apply(function() {
            //             $rootScope.currentvideo = index;
            //             $rootScope.currentpage = index;
            //         });
            //     },500);

            // } else {

            var body = d.documentElement.scrollTop ? d.documentElement : d.body,
                from = body.scrollTop, 
                target = from - Math.abs(d.querySelector('.avatar').getBoundingClientRect().top) - 20;

            $scope.tween = new TWEEN.Tween( { y: from } )
            .to( { y: target }, 600 )
            .easing( TWEEN.Easing.Cubic.Out )
            .onUpdate( function () {
                body.scrollTop = this.y;
            }).start();

            $timeout( function() {
                $rootScope.$apply(function() {
                    $rootScope.currentvideo = index;
                    $rootScope.currentpage = index;
                });
            });                
            // }
        };

        $scope.page = function( direction ) {

            switch ( direction ) {
                case 'left':
                    if ( $rootScope.currentpage > 0 ) {
                        $timeout(function(){
                            $scope.$apply(function(){
                                $rootScope.currentpage--;    
                            });
                        });
                    }
                    break;

                case 'right':
                    if ( $rootScope.currentpage < $scope.items-1 ) {
                        $timeout(function(){
                            $scope.$apply(function(){
                                $rootScope.currentpage++;    
                            });
                        });
                    }
                    break;
            }
        };

        // if ( $scope.touchDevice === false ) {
            $scope.$watch('currentpage', function(newValue, oldValue) {
                d.querySelector('.channel-list').style.left = (-(newValue * 246)) + 'px';
            });    
        // }

        $rootScope.$watch('wW', function(newValue, oldValue){
            if ( $scope.touchDevice === true && newValue < 768 ) {
                d.querySelector('.scroll-outer-wrapper').scrollLeft = 0;
                d.querySelector('.scroll-inner-wrapper').scrollLeft = 0;
                $rootScope.currentpage = 0;
            }
        });

    }]);

    app.controller('PageCtrl', ['$scope', function($scope){}]);


})(window,document,window.angular,'WebLite','controllers');