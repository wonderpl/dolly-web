(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                       [ns + '.services',
                        ns + '.directives'] /* module dependencies */);

    app.controller('MainCtrl', ['$scope', '$timeout','$location', '$rootScope', function($scope, $timeout, $location, $rootScope) {

    	$rootScope.$on('$locationChangeSuccess', function(event){
			$timeout(function(){
        		$rootScope.$apply(function(){
    				$rootScope.currentpage = $location.$$path;
    			});
        	});
    	});

        $rootScope.$on('$locationChangeStart', function(event, newUrl, oldUrl){
        	$timeout(function(){
        		$rootScope.$apply(function(){
        			$rootScope.toggled = false;
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