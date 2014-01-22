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

    app.filter('firstCharUppercase', function(){
        return function(string){ 
            if ( string ) {
                return string.charAt(0).toUpperCase() + string.slice(1);   
            } else {
                return;
            }
        }
    });

    app.filter('firstName', function(){
        return function(string){
            return string.split(' ')[0];
        }
    });

    // app.filter('truncate', function() {
    //     return function (text, length, end) {
    //         if (isNaN(length)) {
    //             length = 10;
    //         }
            
    //         if (end == undefined) {
    //             end = "...";
    //         }
            
    //         if  ( typeof text != "undefined" ) {

    //         }

    //         if (text.length <= length || text.length - end.length <= length) {
    //             return text;
    //         } else {
    //             return String(text).substring(0, length-end.length) + end;
    //         }
    //     }
    // });

})(window,document,window.angular,'WebLite','filters');