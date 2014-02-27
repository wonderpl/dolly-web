(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                       [] /* module dependencies */);


    app.factory('scrollManager', [function(){

        var b = (d.querySelector('.lte9') == null ) ? d.body : d.documentElement;

        var getOffset = function(target){

            var docElem, box = {
                top: 0,
                left: 0
            },

            elem = target,
            doc = elem && elem.ownerDocument;
            docElem = doc.documentElement;

            if (typeof elem.getBoundingClientRect !== undefined ) {
                box = elem.getBoundingClientRect();
            }
            
            return {
                top: box.top + (w.pageYOffset || docElem.scrollTop) - (docElem.clientTop || 0),
                left: box.left + (w.pageXOffset || docElem.scrollLeft) - (docElem.clientLeft || 0)
            };

        };

        var scrollTo = function(target){
            
            var tween = new TWEEN.Tween( { y: b.scrollTop } )
                .to( { y: getOffset(target).top-40 }, 600 )
                .easing( TWEEN.Easing.Cubic.Out )
                .onUpdate( function () {
                    b.scrollTop = this.y
                })
                .start();
        };

        return {
            scrollTo: scrollTo
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


})(window,document,window.angular,'contentApp','services');