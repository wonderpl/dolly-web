(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                       [ns + '.services',
                        ns + '.directives'] /* module dependencies */);

    app.controller('MainCtrl', ['$scope', '$timeout','$location', '$rootScope', 'scrollManager', function($scope, $timeout, $location, $rootScope, scrollManager) {
        
        $rootScope.queueAnchor = false;

    	$rootScope.$on('$locationChangeSuccess', function(event){
			$timeout(function(){
        		$rootScope.$apply(function(){
    				$rootScope.currentpage = $location.$$path;
                    $rootScope.isHomepage = ( $rootScope.currentpage === '/' );

                    if ( $rootScope.queueAnchor !== false ){
                        $timeout( function() {
                            scrollManager.scrollTo( d.getElementById('anchor-' + $rootScope.queueAnchor) );
                            $rootScope.queueAnchor = false;
                        }, 600);    
                    }
                    
    			});
        	});
    	});

        $rootScope.$on('$locationChangeStart', function(event, newUrl, oldUrl){
        	$timeout(function(){
        		$rootScope.$apply(function(){
        			$rootScope.toggled = false;
                    var b = d.documentElement.scrollTop ? d.documentElement : d.body;
                    b.scrollTop = 0;
        		});
        	});
        });

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