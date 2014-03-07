(function(w,d,n,ng,ns) {

    'use strict';

    var app = ng.module(ns /* module name */,
                       [ns + '.controllers',
                        ns + '.services',
                        ns + '.filters',
                        'ngRoute',
                        'ngAnimate'] /* module dependencies */);

    app.config(['$routeProvider', '$interpolateProvider', '$compileProvider', function( $routeProvider, $interpolateProvider, $compileProvider){
        
        // Change the interpolation symbols so they don't conflict with Jinja
        $interpolateProvider.startSymbol('((');
        $interpolateProvider.endSymbol('))');

        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|javascript):/);

        // Add our routes
        $routeProvider.when('/', {templateUrl: 'home.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/our-content', {templateUrl: 'our-content.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/our-categories', {templateUrl: 'our-categories.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/upload', {templateUrl: 'upload.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/partners', {templateUrl: 'partners.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/about-us', {templateUrl: 'about-us.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
        $routeProvider.when('/faq', {templateUrl: 'faq.html', resolve: { trackingCode: function (GATrackingService) { return GATrackingService.push(); }}});
    }]);

    app.run(['$timeout', '$rootScope', 'animLoop' , function($timeout, $rootScope, animLoop) {

        // Cache the assets URL
        $rootScope.assets_url = window.assets_url;

        // The loaded state of the Google Maps API
        $rootScope.mapsLoaded = false;

        // Initialise our animLoop service, and add our TWEEN loop
        animLoop.setFPS(60);
        animLoop.add('tween', TWEEN.update);
        animLoop.add('checkMapsLoaded', function(){
            if ( window.mapsAPILoaded === true ) {
                $timeout(function(){
                    $rootScope.$apply(function(){
                        $rootScope.mapsLoaded = true;
                    });
                });
                animLoop.remove('checkMapsLoaded');
            }
        });
        animLoop.start();

    }]);

})(window,document,navigator,window.angular,'contentApp');

// Setting up a maps loaded listener
window.mapsAPILoaded = false;
window.mapsloaded = function () {
    window.mapsAPILoaded = true;
};