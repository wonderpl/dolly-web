describe("UserManager", function () {
  describe ('The UserManager service data should reflect user state (login/logout)', function() {
    window.apiUrls = jQuery.parseJSON('{"cover_art": "http://myrockpack.com/ws/cover_art/?locale=en-us", "channel_search_terms": "http://myrockpack.com/ws/complete/channels/?locale=en-us", "register": "http://myrockpack.com/ws/register/", "categories": "http://myrockpack.com/ws/categories/?locale=en-us", "reset_password": "http://myrockpack.com/ws/reset-password/", "video_search": "http://myrockpack.com/ws/search/videos/?locale=en-us", "channel_search": "http://myrockpack.com/ws/search/channels/?locale=en-us", "video_search_terms": "http://myrockpack.com/ws/complete/videos/?locale=en-us", "popular_channels": "http://myrockpack.com/ws/channels/?locale=en-us", "popular_videos": "http://myrockpack.com/ws/videos/?locale=en-us", "login": "http://myrockpack.com/ws/login/", "login_register_external": "http://myrockpack.com/ws/login/external/", "refresh_token": "http://myrockpack.com/ws/token/"}');
    beforeEach(module('WebApp' ,'mockLogin'));
    it('Should store date on login', inject(function(UserManager) {
       console.log (UserManager);
       UserManager.Login('test','testtest');
       console.log (UserManager);
    }))
  })
})