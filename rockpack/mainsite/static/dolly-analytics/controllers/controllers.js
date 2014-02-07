(function(w,d,ng,ns,m) {

    'use strict';

    var app = ng.module(ns + '.' + m /* module name */,
                       [ns + '.services',
                        ns + '.directives'] /* module dependencies */);

    app.controller('MainCtrl', ['$scope', '$timeout','$location', '$rootScope', '$http', '$templateCache', '$compile', function($scope, $timeout, $location, $rootScope, $http, $templateCache, $compile) {

        var template, tmpl;
        $scope.videos = {};
        $scope.data = {};
        $scope.metrics = {};

        $http({method: 'get', url: 'http://127.0.0.1:5000/ws/analytics/-/'}).success(function(data,status,headers,config){
            $timeout(function(){
                $scope.$apply(function(){
                    console.log(data);
                    $scope.videos = data.videos.items;
                });
            });
        });

        $scope.loadVideo = function (url) {
            $http({method: 'get', url: url + '?start=2014-01-15&end=2014-02-07' }).success(function(data,status,headers,config){
                $timeout(function(){
                    $scope.$apply(function(){
                        console.log(data);
                        $scope.metrics = data.metrics;
                    });
                });
            });
        }

        $scope.$watch( 'metrics', function(newValue){

            $scope.config = {
                labels: false,
                title : "Video metrics",
                legend : {
                    display:true,
                    position:'left'
                }
            };
            $scope.data.series = [
              "Total Plays",
              "Unique Plays"
            ];
            $scope.data.data = [];

            $scope.chartConfig = {
                "options": {
                    "width": 400,
                    "chart": {
                        "type": "spline"
                    },
                    "plotOptions": {
                        "series": {
                            "stacking": ""
                        }
                    }
                },
                "xAxis": {
                    "categories": []
                },
                "yAxis": {
                    "title": {
                        "text": "Plays"
                    }
                },
                "series": [
                {
                    "name": "Plays",
                    "data": [],
                    "id": "series-0",
                    "color": "red"
                },
                {
                    "name": "Unique Plays",
                    "data": [],
                    "id": "series-1"
                }
                ],
                "title": {
                    "text": "Video metrics"
                },
                "credits": {
                    "enabled": false
                },
                "loading": false,
                "width": 200
            };

            for ( var i = 0; i < $scope.metrics.length; i++ ) {
                $scope.chartConfig.xAxis.categories.push( moment( new Date($scope.metrics[i].date) ).format("MMM Do YY") );
                $scope.chartConfig.series[0].data.push($scope.metrics[i].plays);
                $scope.chartConfig.series[1].data.push($scope.metrics[i].daily_uniq_plays);
            }

            if ( $scope.metrics.length > 0 ){
                $timeout( function() {
                    $scope.$apply(function(){
                        template = $templateCache.get('graph.html');
                        console.log(template);
                        tmpl = $compile(template)($scope);
                        ng.element(d.getElementById('chart-wrapper')).html(tmpl);
                    });
                });    
            }
            
        });

        

    }]);    

})(window,document,window.angular,'AnalyticsApp','controllers');