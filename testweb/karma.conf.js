// Karma configuration
// Generated on Fri Jun 14 2013 14:09:06 GMT+0100 (BST)


// base path, that will be used to resolve files and exclude
basePath = '';


// list of files / patterns to load in the browser
files = [
  JASMINE,
  JASMINE_ADAPTER,
  '../rockpack/mainsite/static/assets/vendor/js/angular.js',
  'angular-mocks.js',
  '../rockpack/mainsite/static/assets/vendor/js/ng-infinite-scroll.js',
  '../rockpack/mainsite/static/assets/vendor/js/ui-bootstrap-tpls-0.3.0.js',
  '../rockpack/mainsite/static/assets/vendor/js/jquery-1.9.1.js',
  '../rockpack/mainsite/static/fullwebapp/**/*.coffee',
  'tests/*.js',
  'mocks//.js'
];


// list of files to exclude
exclude = [
  
];

preprocessors = {
    '../rockpack/mainsite/static/fullwebapp/**/*.coffee': 'coffee'
};

// test results reporter to use
// possible values: 'dots', 'progress', 'junit'
reporters = ['progress'];


// web server port
port = 9876;


// cli runner port
runnerPort = 9100;


// enable / disable colors in the output (reporters and logs)
colors = true;


// level of logging
// possible values: LOG_DISABLE || LOG_ERROR || LOG_WARN || LOG_INFO || LOG_DEBUG
logLevel = LOG_INFO;


// enable / disable watching file and executing tests whenever any file changes
autoWatch = true;


// Start these browsers, currently available:
// - Chrome
// - ChromeCanary
// - Firefox
// - Opera
// - Safari (only Mac)
// - PhantomJS
// - IE (only Windows)
browsers = ['Chrome'];


// If browser does not capture in given timeout [ms], kill it
captureTimeout = 60000;


// Continuous Integration mode
// if true, it capture browsers, run tests and exit
singleRun = false;
