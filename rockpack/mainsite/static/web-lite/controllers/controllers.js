(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
        [ns + '.services',
        ns + '.directives'] /* module dependencies */);

    app.controller('WebLiteCtrl', ['$scope', '$timeout','$location', '$rootScope', '$templateCache', '$sanitize', '$compile', '$http', 'querystring', 'userService', function($scope, $timeout, $location, $rootScope, $templateCache, $sanitize, $compile, $http, querystring, userService) {

        $rootScope.weblite = true;
        $rootScope.assets_url = window.assets_url;
        $rootScope.selected_video = window.selected_video || {};
        $rootScope.channel_data = window.channel_data;
        $rootScope.owner = window.channel_data.owner;
        $rootScope.videos = Array.prototype.slice.call( $rootScope.channel_data.videos.items );
        $rootScope.api = window.apiUrls;

        var shareuser = querystring.search('shareuser');

        if ( shareuser.length > 0 ) {
            userService.fetchUser($rootScope.user.id);
        } else {
            $rootScope.shareuser = $rootScope.owner;
        }

        // Get the array index 
        var searchid = querystring.search( 'video' );

        if ( searchid.length > 0 ) {
            ng.forEach( $rootScope.videos, function( el, i) {
                if ( el.id === searchid ) {
                    $rootScope.currentvideo = i;
                }
            });    
        } else {
            $rootScope.currentvideo = 0;
        }

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

    }]);


    app.controller('ChannelCtrl', ['$scope', '$timeout','$location', '$rootScope', '$templateCache', '$sanitize', '$compile', function($scope, $timeout, $location, $rootScope, $templateCache, $sanitize, $compile) {

        var $this = ng.element(d.getElementById('channel')),
        template, 
        $scp, 
        tmpl;

        $scope.currentpage = 0;
        $scope.items = $rootScope.videos.length;
        $scope.touchDevice = 'ontouchstart' in window || 'onmsgesturechange' in window;

        ng.extend($scope, $rootScope.channel_data);
        template = $templateCache.get('channel.html');
        tmpl = $compile(template)($scope);
        $this.html('').append(tmpl);

        $scope.changeVideo = function(e, index) {
            e.preventDefault();
                        
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
                    $scope.currentpage = index;
                });
            });
        };

        $scope.page = function( direction ) {

            switch ( direction ) {
                case 'left':
                    if ( $scope.currentpage > 0 ) {
                        $timeout(function(){
                            $scope.$apply(function(){
                                $scope.currentpage--;    
                            });
                        });
                    }
                    break;

                case 'right':
                    console.log($scope.items);
                    if ( $scope.currentpage < $scope.items-1 ) {
                        $timeout(function(){
                            $scope.$apply(function(){
                                console.log('here');
                                $scope.currentpage++;    
                            });
                        });
                    }
                    break;
            }
        };

        if ( $scope.touchDevice === false ) {
            $scope.$watch('currentpage', function(newValue, oldValue) {
                d.querySelector('.channel-list').style.left = (-(newValue * 246)) + 'px';
                console.log((-(newValue * 246)) + 'px');
            });    
        }

    }]);


    app.controller('HeaderCtrl', ['$scope', '$timeout','$rootScope', function($scope, $timeout, $rootScope){

        $rootScope.toggled = false;

        $rootScope.navToggle = function() {
            $timeout(function(){
                $rootScope.$apply(function(){
                    if ( $rootScope.toggled === true ) {
                        $rootScope.toggled = false;
                    } else {
                        $rootScope.toggled = true;
                    }
                });
            });  		
        };

    }]);

    app.controller('PageCtrl', ['$scope', function($scope){}]);


})(window,document,window.angular,'WebLite','controllers');