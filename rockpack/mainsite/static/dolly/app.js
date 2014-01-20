(function(w,d,n,ng,ns) {

    'use strict';

    var app = ng.module(ns /* module name */,
                       [ns + '.controllers',
                        ns + '.services',
                        ns + '.filters',
                        'ngRoute',
                        'ngAnimate'] /* module dependencies */);

    app.config(['$routeProvider', '$interpolateProvider', '$compileProvider', function( $routeProvider, $interpolateProvider, $compileProvider){
        $interpolateProvider.startSymbol('((');
        $interpolateProvider.endSymbol('))');
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|javascript):/);

        $routeProvider.when('/', {templateUrl: 'home.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/our-content', {templateUrl: 'our-content.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/our-categories', {templateUrl: 'our-categories.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/upload', {templateUrl: 'upload.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/partners', {templateUrl: 'partners.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/about-us', {templateUrl: 'about-us.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});

        $routeProvider.when('/web-lite', {templateUrl: 'web-lite.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
    }]);

    app.run(['$timeout', '$rootScope', 'animLoop', function($timeout, $rootScope, animLoop) {
        $rootScope.assets_url = window.assets_url;

        // Initialise our animLoop service, and add our TWEEN loop
        animLoop.setFPS(60);
        animLoop.add('tween', TWEEN.update);
        animLoop.start();
    }]);

})(window,document,navigator,window.angular,'contentApp');