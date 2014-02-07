(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                        [] /* module dependencies */);

    app.filter('slugify', function() {
        return function(input) {
            return input.toLowerCase().split('é').join('e').replace(/[^\w\s-]/g, "").replace(/[-\s]+/g, "-");
        };
    });

    app.filter('asset', ['MOBILE', function(MOBILE) {
        return function(input) {
            if (MOBILE) {
                input = input.split('.png').join('-mobile.png').split('.jpg').join('-mobile.jpg');
            }
            return input;
        };
    }]);

    app.filter('reverse', function() {
        return function(items) {
            return items.slice().reverse();
        };
    });

})(window,document,window.angular,'AnalyticsApp','filters');