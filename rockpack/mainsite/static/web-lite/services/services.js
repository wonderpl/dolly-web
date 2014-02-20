(function(w,d,ng,ns,m) {


    'use strict';


    var app = ng.module(ns + '.' + m /* module name */,
                       [] /* module dependencies */);

    app.factory('UserService', ['$rootScope', '$http', '$timeout', function($rootScope, $http, $timeout){
        return {
            fetchUser: function(id) {
                $http({method: 'get', url: $rootScope.api.base_api + id + '/' }).success(function(data,status,headers,config){
                    $timeout(function(){
                        $rootScope.$apply(function(){
                            $rootScope.user = data;
                        });
                    });
                });
            }
        }
    }]);


    app.factory('$sanitize', [function() {
        return function(input) {
            return input.replace('\n', '').replace('\t', '').replace('\r', '').replace(/^\s+/g, '');
        };
    }]);


    app.factory('GATrackingService', function($route) {
        return {
            push: function () {
                return ga('send', 'pageview', $route.current.$$route.templateUrl);
            }
        }
    });


    app.factory('querystring', function(){
        return {
            search: function(name){
                name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
                var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
                results = regex.exec(location.search);
                return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
            }
        }
    });


    app.factory('windowSize', ['$timeout', function($timeout){
    
        var ww = (function() {
            if (typeof w.innerWidth !== 'undefined') {
                return function() {
                    return w.innerWidth;
                };
            } else {
                var b = ('clientWidth' in d.documentElement) ? d.documentElement : d.body;
                return function() {
                    return b.clientWidth;
                };
            }
        })();

        var wh = (function() {
            if (typeof w.innerHeight !== 'undefined') {
                return function() {
                    return w.innerHeight;
                };
            } else {
                var b = ('clientHeight' in d.documentElement) ? d.documentElement : d.body;
                return function() {
                    return b.clientHeight;
                };
            }
        })();

        return {
            ww: ww,
            wh: wh
        };
    }]);


    app.factory('windowResizer', ['$timeout', '$rootScope', 'windowSize', 'animLoop', function($timeout, $rootScope, windowSize, animLoop) {

        var wW = windowSize.ww(),
            wH = windowSize.wh();

        var resize = function(){
            $timeout( function() {
                $rootScope.$apply(function() {
                    $rootScope.wW = wW;
                    $rootScope.wH = wH;
                })
            });

            animLoop.remove('windowResize');
        }

        w.onresize = function() {
            wW = windowSize.ww();
            wH = windowSize.wh();
            animLoop.add('windowResize', resize);
        };
    }]);

    app.factory('animLoop', function(){

        var rafLast = 0;

        var requestAnimFrame = (function(){
            return  window.requestAnimationFrame     ||
            window.webkitRequestAnimationFrame ||
            window.mozRequestAnimationFrame    ||
            function(callback, element) {
                var currTime = new Date().getTime();
                var timeToCall = Math.max(0, 16 - (currTime - rafLast));
                var id = window.setTimeout(function() { callback(currTime + timeToCall); }, timeToCall);
                rafLast = currTime + timeToCall;
                return id;
            };
        })();

        var cancelAnimFrame = (function() {
            return  window.cancelAnimationFrame        ||
            window.cancelRequestAnimationFrame   ||
            window.webkitCancelAnimationFrame    ||
            window.webkitCancelRequestAnimationFrame ||
            window.mozCancelAnimationFrame     ||
            window.mozCancelRequestAnimationFrame  ||
            function(id) {
                clearTimeout(id);
            };
        })();

        var FramePipeline = function() {
            var _t = this;
            _t.pipeline = {};
            _t.then = new Date().getTime();
            _t.now = undefined;
            _t.raf = undefined;
            _t.delta = undefined;
            _t.interval = 1000 / 60;
            _t.running = false;
        };

        FramePipeline.prototype = {
            add : function(name, fn) {
                this.pipeline[name] = fn;
            },
            remove : function(name) {
                delete this.pipeline[name];
            },
            start : function() {
                if (!this.running) {
                    this._tick();
                    this.running = true;
                }
            },
            pause : function() {
                if (this.running) {
                    cancelAnimFrame.call(window, this.raf);
                    this.running = false;
                }         
            },
            setFPS : function(fps) {
                this.interval = 1000 / fps;
            },
            _tick : function tick() {
                var _t = this;
                _t.raf = requestAnimFrame.call(window, tick.bind(_t));
                _t.now = new Date().getTime();
                _t.delta = _t.now - _t.then;
                if (_t.delta > _t.interval) {
                    for (var n in _t.pipeline) {
                        _t.pipeline[n]();
                    }
                    _t.then = _t.now - (_t.delta % _t.interval);
                }
            }
        };

        var pipeline = new FramePipeline();

        Function.prototype.bind = Function.prototype.bind || function() {
            return function(context) {
                var fn = this,
                args = Array.prototype.slice.call(arguments, 1);

                if (args.length) {
                    return function() {
                        return arguments.length ? fn.apply(context, args.concat(Array.prototype.slice.call(arguments))) : fn.apply(context, args);
                    };
                }
                return function() {
                    return arguments.length ? fn.apply(context, arguments) : fn.apply(context);
                };
            };
        };

        return pipeline;
    });

})(window,document,window.angular,'WebLite','services');