(function(w,d,n,ng,ns) {

    'use strict';

    var app = ng.module(ns /* module name */,
                       [ns + '.controllers',
                        ns + '.services',
                        ns + '.filters',
                        'ngRoute',
                        'ngAnimate',
                        'ngSanitize'] /* module dependencies */);

    app.config(['$interpolateProvider', '$compileProvider', function( $interpolateProvider, $compileProvider){
        $interpolateProvider.startSymbol('((');
        $interpolateProvider.endSymbol('))');
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|javascript):/);
    }]);

    app.run(['$timeout', '$rootScope', 'animLoop', function($timeout, $rootScope, animLoop) {
        window.onkeydown = function(e) { 
            // d.getElementById('wonderplayer').getElementsByTagName('iframe')[0].contentWindow.focus();
            return !(e.keyCode == 32);
        };

        // Initialise our animLoop service, and add our TWEEN loop
        animLoop.setFPS(60);
        animLoop.add('tween', TWEEN.update);
        animLoop.start();
    }]);

})(window,document,navigator,window.angular,'WebLite');