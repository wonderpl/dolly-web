(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                       [ns + '.services',
                        ns + '.directives'] /* module dependencies */);

    app.controller('MainCtrl', ['$scope', '$timeout','$location', '$rootScope', function($scope, $timeout, $location, $rootScope) {

        $rootScope.queueAnchor = false;

    	$rootScope.$on('$locationChangeSuccess', function(event){
			$timeout(function(){
        		$rootScope.$apply(function(){
    				$rootScope.currentpage = $location.$$path;

                    if ( $location.path() === '/about-us' &&  $rootScope.queueAnchor !== false ) {
                        $timeout( function(){
                            $rootScope.scrollToAnchor(d.getElementById('anchor-' + $rootScope.queueAnchor))
                            $rootScope.queueAnchor = false;
                        }, 200)
                    }
    			});
        	});
    	});

        $rootScope.$on('$locationChangeStart', function(event, newUrl, oldUrl){
            console.log('location change started');
        	$timeout(function(){
        		$rootScope.$apply(function(){
        			$rootScope.toggled = false;
                    var b = d.documentElement.scrollTop ? d.documentElement : d.body;
                    b.scrollTop = 0;
        		});
        	});
        });

        $rootScope.scrollToAnchor = function( target ) {
            var body = d.documentElement.scrollTop ? d.documentElement : d.body,
                from = body.scrollTop,
                to = ng.element(target).offset().top,
                tween;

                $('body, html').animate({scrollTop: to}, 600);

            // tween = new TWEEN.Tween( { y: from } )
            // .to( { y: to-75 }, 600 )
            // .easing( TWEEN.Easing.Cubic.Out )
            // .onUpdate( function () {
            //     console.log(this.y);
            //     body.scrollTop = this.y;
            // }).start();

            // if ( ng.element(d.getElementsByTagName('html')).hasClass('ie8') ) {
            //     $timeout(function(){
            //         body.scrollTop = to;
            //     }, 100);
            // }
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

    app.controller('PageCtrl', ['$scope', function($scope){

    }]);

})(window,document,window.angular,'contentApp','controllers');