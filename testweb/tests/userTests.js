describe("UserManager Service Testing", function() {

    var refreshToken = {"token_type":"Bearer","user_id":"CeGfSz6dQW2ga2P2tKb3Bg","access_token":"ef235de46dba53ba69ed049f57496ec902da5d28AAFB1HdeTE-2vwnhn0s-nUFtoGtj9rSm9waiuhySCpFJxKVYqOx9W7Gt","resource_url":"http://myrockpack.com/ws/CeGfSz6dQW2ga2P2tKb3Bg/","expires_in":3600,"refresh_token":"873e06747d964a0d80f79181c98aceac"};

    beforeEach(angular.mock.module('WebApp'));

    beforeEach(inject(function($httpBackend) {
        window.apiUrls = jQuery.parseJSON('{"cover_art": "http://myrockpack.com/ws/cover_art/?locale=en-us", "channel_search_terms": "http://myrockpack.com/ws/complete/channels/?locale=en-us", "register": "http://myrockpack.com/ws/register/", "categories": "http://myrockpack.com/ws/categories/?locale=en-us", "reset_password": "http://myrockpack.com/ws/reset-password/", "share_url": "http://myrockpack.com/ws/share/link/", "video_search": "http://myrockpack.com/ws/search/videos/?locale=en-us", "channel_search": "http://myrockpack.com/ws/search/channels/?locale=en-us", "video_search_terms": "http://myrockpack.com/ws/complete/videos/?locale=en-us", "popular_channels": "http://myrockpack.com/ws/channels/?locale=en-us", "popular_videos": "http://myrockpack.com/ws/videos/?locale=en-us", "login": "http://myrockpack.com/ws/login/", "login_register_external": "http://myrockpack.com/ws/login/external/", "refresh_token": "http://myrockpack.com/ws/token/"}');
        $httpBackend.when('POST', window.apiUrls.refresh_token).respond(refreshToken);
    }));

    it('should contain an UserManage service', inject(function(UserManager) {
        expect(UserManager).not.toEqual(null);
    }));

    it('UserManager should allow user Login', inject(function(UserManager, $httpBackend) {
        var mockLogin = {"token_type":"Bearer","user_id":"oCRwcy5MRIiWmsJjvbFbHA","access_token":"752a4f939662846a787a1474ad17ffddcd816dc7AAFB1G7HvgH-0qAkcHMuTESIlprCY72xWxyiuhySCpFJxKVYqOx9W7Gt","resource_url":"http://myrockpack.com/ws/oCRwcy5MRIiWmsJjvbFbHA/","expires_in":2,"refresh_token":"fa2f47f3590240e4bdfdbde03bf8042d"}
        $httpBackend.when('POST', window.apiUrls.login).respond(mockLogin);
        UserManager.oauth.Login('gtest','qweqwe');
        $httpBackend.flush();
        var loggedUser = {
            token_type: 'Bearer',
            user_id: 'oCRwcy5MRIiWmsJjvbFbHA',
            access_token: '752a4f939662846a787a1474ad17ffddcd816dc7AAFB1G7HvgH-0qAkcHMuTESIlprCY72xWxyiuhySCpFJxKVYqOx9W7Gt',
            resource_url: 'http://myrockpack.com/ws/oCRwcy5MRIiWmsJjvbFbHA/',
            expires_in: 2,
            refresh_token: 'fa2f47f3590240e4bdfdbde03bf8042d'
        }

        expect(UserManager.oauth.credentials).toEqual(loggedUser);
        expect(UserManager.oauth.isLoggedIn).toEqual(true);
    }));


    it('UserManager should allow user Login', inject(function(UserManager, $httpBackend) {
        UserManager.logOut();
        expect(UserManager.oauth.credentials).toEqual({});
        expect(UserManager.oauth.isLoggedIn).toEqual(false);
    }));

});

// Unable to test refresh token callback, reciving a 'No pending request to flush' error even after request is made

//describe("UserManager Service Testing", function() {
//
//    beforeEach(angular.mock.module('WebApp'));
//
//    beforeEach(inject(function($httpBackend) {
//        window.apiUrls = jQuery.parseJSON('{"cover_art": "http://myrockpack.com/ws/cover_art/?locale=en-us", "channel_search_terms": "http://myrockpack.com/ws/complete/channels/?locale=en-us", "register": "http://myrockpack.com/ws/register/", "categories": "http://myrockpack.com/ws/categories/?locale=en-us", "reset_password": "http://myrockpack.com/ws/reset-password/", "share_url": "http://myrockpack.com/ws/share/link/", "video_search": "http://myrockpack.com/ws/search/videos/?locale=en-us", "channel_search": "http://myrockpack.com/ws/search/channels/?locale=en-us", "video_search_terms": "http://myrockpack.com/ws/complete/videos/?locale=en-us", "popular_channels": "http://myrockpack.com/ws/channels/?locale=en-us", "popular_videos": "http://myrockpack.com/ws/videos/?locale=en-us", "login": "http://myrockpack.com/ws/login/", "login_register_external": "http://myrockpack.com/ws/login/external/", "refresh_token": "http://myrockpack.com/ws/token/"}');
//        var mockLogin = {"token_type":"Bearer","user_id":"oCRwcy5MRIiWmsJjvbFbHA","access_token":"752a4f939662846a787a1474ad17ffddcd816dc7AAFB1G7HvgH-0qAkcHMuTESIlprCY72xWxyiuhySCpFJxKVYqOx9W7Gt","resource_url":"http://myrockpack.com/ws/oCRwcy5MRIiWmsJjvbFbHA/","expires_in":2,"refresh_token":"fa2f47f3590240e4bdfdbde03bf8042d"}
//        var refreshToken = {"token_type":"Bearer","user_id":"CeGfSz6dQW2ga2P2tKb3Bg","access_token":"ef235de46dba53ba69ed049f57496ec902da5d28AAFB1HdeTE-2vwnhn0s-nUFtoGtj9rSm9waiuhySCpFJxKVYqOx9W7Gt","resource_url":"http://myrockpack.com/ws/CeGfSz6dQW2ga2P2tKb3Bg/","expires_in":3600,"refresh_token":"873e06747d964a0d80f79181c98aceac"};
//        $httpBackend.when('POST', window.apiUrls.refresh_token).respond(refreshToken);
//        $httpBackend.when('POST', window.apiUrls.login).respond(mockLogin);
//    }));
//
//    it('UserManager should refresh the token after 2 seconds', inject(function(UserManager, $httpBackend) {
//        UserManager.oauth.Login('gtest','qweqwe');
//        $httpBackend.flush();
//        waits(4000);
//        $httpBackend.flush();
//        expect(UserManager.oauth.credentials.access_token).toEqual('ef235de46dba53ba69ed049f57496ec902da5d28AAFB1HdeTE-2vwnhn0s-nUFtoGtj9rSm9waiuhySCpFJxKVYqOx9W7Gt');
//    }));
//
//});