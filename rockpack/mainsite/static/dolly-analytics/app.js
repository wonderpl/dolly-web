(function(w,d,n,ng,ns) {

    'use strict';

    var app = ng.module(ns /* module name */,
                       [ns + '.controllers',
                        ns + '.services',
                        ns + '.filters',
                        'highcharts-ng'
                        ] /* module dependencies */);


    app.config(['$interpolateProvider', function($interpolateProvider){
        $interpolateProvider.startSymbol('((');
        $interpolateProvider.endSymbol('))');
    }]);

    app.run(['$timeout', '$rootScope', 'animLoop', function($timeout, $rootScope, animLoop) {
        // animLoop.setFPS(60);
        // animLoop.start();
    }]);

})(window,document,navigator,window.angular,'AnalyticsApp');