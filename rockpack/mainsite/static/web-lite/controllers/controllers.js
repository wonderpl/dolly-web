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

        console.log( $rootScope.channel_data );

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

    }]);


    app.controller('ChannelCtrl', ['$scope', '$timeout','$location', '$rootScope', '$templateCache', '$sanitize', '$compile', function($scope, $timeout, $location, $rootScope, $templateCache, $sanitize, $compile) {

        var $this = ng.element(d.getElementById('channel')),
        template, 
        $scp, 
        tmpl;

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
                });
            });
        };

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