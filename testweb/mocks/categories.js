'use strict';

angular.module('mockCategories', [])
    .value('defaultJSON', {"categories":{"items":[{"priority":11000,"sub_categories":[{"priority":80,"name":"Metal","id":"125"},{"priority":90,"name":"Rock","id":"124"},{"priority":70,"name":"Electronic","id":"126"},{"priority":120,"name":"Pop","id":"123"},{"priority":-1,"name":"Dubstep","id":"127"},{"priority":10,"name":"How-to","id":"453"},{"priority":100,"name":"Hip Hop","id":"128"},{"priority":110,"name":"RnB","id":"130"},{"priority":20,"name":"Karaoke","id":"451"},{"priority":30,"name":"Disco","id":"129"},{"priority":-2,"name":"Folk","id":"131"},{"priority":-3,"name":"World","id":"132"},{"priority":-4,"name":"Latin","id":"133"},{"priority":-5,"name":"Jazz","id":"134"},{"priority":50,"name":"Classical","id":"135"},{"priority":-6,"default":true,"name":"Other","id":"136"},{"priority":60,"name":"Soundtracks","id":"450"},{"priority":40,"name":"Country","id":"452"},{"priority":-7,"name":"Dance","id":"467"}],"name":"Music","id":"122"},{"priority":10000,"sub_categories":[{"priority":100,"name":"Xbox ","id":"139"},{"priority":-5,"name":"IOS","id":"144"},{"priority":-4,"name":"Android","id":"145"},{"priority":20,"name":"Retro","id":"146"},{"priority":-1,"name":"Wii U","id":"140"},{"priority":-2,"name":"3DS ","id":"141"},{"priority":-3,"name":"VITA","id":"142"},{"priority":70,"name":"PC","id":"143"},{"priority":90,"name":"Playstation","id":"138"},{"priority":-6,"name":"Interview","id":"149"},{"priority":-7,"default":true,"name":"Other","id":"150"},{"priority":80,"name":"Nintendo","id":"368"},{"priority":-8,"name":"Delete","id":"382"},{"priority":30,"name":"Walkthroughs","id":"147"},{"priority":50,"name":"eSports","id":"148"},{"priority":40,"name":"Gamers","id":"366"},{"priority":10,"name":"Mobile","id":"369"},{"priority":60,"name":"Reviews","id":"373"}],"name":"Gaming","id":"137"},{"priority":5000,"sub_categories":[{"priority":70,"name":"Designers","id":"191"},{"priority":20,"name":"Street style","id":"194"},{"priority":10,"name":"Men","id":"196"},{"priority":40,"name":"Accessories","id":"198"},{"priority":60,"name":"Beauty","id":"199"},{"priority":-1,"name":"Runway","id":"192"},{"priority":-2,"name":"Shopping","id":"193"},{"priority":-3,"name":"Front row","id":"195"},{"priority":-4,"name":"Interview","id":"197"},{"priority":-5,"default":true,"name":"Other","id":"200"},{"priority":80,"name":"Fashion","id":"374"},{"priority":-6,"name":"Luxury","id":"462"},{"priority":30,"name":"Star Style","id":"463"},{"priority":50,"name":"Hairdressing","id":"464"}],"name":"Style","id":"190"},{"priority":4000,"sub_categories":[{"priority":70,"name":"Design","id":"202"},{"priority":-1,"name":"Art","id":"203"},{"priority":110,"name":"Health","id":"208"},{"priority":50,"name":"Interiors","id":"204"},{"priority":90,"name":"Cars","id":"205"},{"priority":80,"name":"Bikes","id":"206"},{"priority":-5,"name":"Family ","id":"207"},{"priority":-2,"name":"Travel","id":"209"},{"priority":30,"name":"Craft","id":"210"},{"priority":-3,"default":true,"name":"Other","id":"211"},{"priority":-4,"name":"Recreation","id":"442"},{"priority":20,"name":"Gardening","id":"446"},{"priority":10,"name":"Kids & Family","id":"443"},{"priority":40,"name":"Pets","id":"444"},{"priority":100,"name":"Fitness","id":"445"},{"priority":60,"name":"Men's Health","id":"447"}],"name":"Living","id":"201"},{"priority":3000,"sub_categories":[{"priority":20,"name":"Causes","id":"435"},{"priority":90,"name":"Education","id":"436"},{"priority":80,"name":"Business","id":"437"},{"priority":-2,"name":"Kids & Family","id":"438"},{"priority":110,"name":"Tech","id":"213"},{"priority":30,"name":"History","id":"214"},{"priority":50,"name":"Nature","id":"215"},{"priority":-3,"name":"Hands-on","id":"218"},{"priority":60,"name":"Science","id":"216"},{"priority":40,"name":"Talks","id":"217"},{"priority":100,"name":"News","id":"220"},{"priority":-5,"default":true,"name":"Other","id":"221"},{"priority":-6,"name":"Literature ","id":"439"},{"priority":-7,"name":"Men's health","id":"376"},{"priority":-8,"name":"Creative","id":"440"},{"priority":10,"name":"How-to","id":"441"},{"priority":70,"name":"Art","id":"466"}],"name":"Genius","id":"212"},{"priority":2000,"sub_categories":[{"priority":20,"name":"Cuisines","id":"432"},{"priority":-10,"name":"How-to","id":"434"},{"priority":-1,"name":"Funny","id":"433"},{"priority":50,"name":"Chefs","id":"236"},{"priority":80,"name":"Recipes","id":"237"},{"priority":60,"name":"Healthy","id":"238"},{"priority":40,"name":"Drinks","id":"239"},{"priority":70,"name":"Baking","id":"240"},{"priority":-2,"default":true,"name":"Other","id":"242"},{"priority":30,"name":"Restaurants","id":"241"}],"name":"Food","id":"235"},{"priority":6000,"sub_categories":[{"priority":50,"name":"Golf","id":"230"},{"priority":30,"name":"Soccer","id":"231"},{"priority":60,"name":"Tennis","id":"232"},{"priority":70,"name":"Boxing","id":"233"},{"priority":-1,"name":"NFL","id":"223"},{"priority":-2,"name":"MLB","id":"224"},{"priority":-3,"name":"NBA","id":"225"},{"priority":-4,"name":"NHL","id":"226"},{"priority":-5,"name":"NCAAF","id":"227"},{"priority":-6,"name":"NCAAM","id":"228"},{"priority":-7,"name":"Nascar","id":"229"},{"priority":110,"name":"Basketball","id":"379"},{"priority":20,"name":"Extreme","id":"375"},{"priority":120,"name":"Football","id":"378"},{"priority":100,"name":"Baseball","id":"380"},{"priority":40,"name":"Motorsport","id":"381"},{"priority":-9,"default":true,"name":"Other","id":"234"},{"priority":-8,"name":"Philosophy","id":"459"},{"priority":80,"name":"MMA","id":"460"},{"priority":90,"name":"Hockey","id":"470"},{"priority":-11,"name":"How-to","id":"461"}],"name":"Sports","id":"222"},{"priority":8000,"sub_categories":[{"priority":50,"name":"Drama","id":"158"},{"priority":110,"name":"Sci-fi","id":"154"},{"priority":120,"name":"Action","id":"155"},{"priority":100,"name":"Fantasy","id":"156"},{"priority":80,"name":"Comedy","id":"152"},{"priority":40,"name":"Thriller","id":"153"},{"priority":60,"name":"Horror","id":"159"},{"priority":70,"name":"Romance","id":"160"},{"priority":-2,"name":"Anime","id":"157"},{"priority":10,"name":"Musicals","id":"161"},{"priority":30,"name":"World","id":"162"},{"priority":-1,"default":true,"name":"Other","id":"163"},{"priority":20,"name":"Classics","id":"449"},{"priority":90,"name":"Family","id":"448"}],"name":"Movies","id":"151"},{"priority":1000,"sub_categories":[{"priority":90,"name":"Cities","id":"401"},{"priority":40,"name":"Activities","id":"402"},{"priority":-1,"name":"Food","id":"404"},{"priority":50,"name":"Kids & Family","id":"405"},{"priority":60,"name":"Hotels","id":"406"},{"priority":70,"name":"Winter","id":"407"},{"priority":80,"name":"Summer","id":"403"},{"priority":10,"name":"How-to","id":"410"},{"priority":20,"name":"Backpacking","id":"408"},{"priority":-2,"default":true,"name":"Other","id":"411"},{"priority":-3,"name":"Outdoors","id":"409"},{"priority":30,"name":"Sightseeing","id":"471"}],"name":"Travel","id":"400"},{"priority":7000,"sub_categories":[{"priority":50,"name":"LOL","id":"178"},{"priority":70,"name":"Comedians","id":"179"},{"priority":30,"name":"Sketches","id":"180"},{"priority":40,"name":"Satire","id":"182"},{"priority":-1,"default":true,"name":"Other","id":"183"},{"priority":60,"name":"Stand-up","id":"181"},{"priority":20,"name":"Animals","id":"468"},{"priority":10,"name":"Fails","id":"469"}],"name":"Comedy","id":"386"},{"priority":9000,"sub_categories":[{"priority":-1,"name":"Animals","id":"427"},{"priority":-3,"default":true,"name":"Other","id":"170"},{"priority":70,"name":"Series","id":"165"},{"priority":-2,"name":"Shows","id":"166"},{"priority":40,"name":"Reality ","id":"167"},{"priority":-5,"name":"Ads","id":"168"},{"priority":50,"name":"Celebrities","id":"169"},{"priority":30,"name":"Animation","id":"377"},{"priority":-4,"name":"Fails","id":"428"},{"priority":20,"name":"Documentary","id":"429"},{"priority":10,"name":"Kids & Family","id":"430"},{"priority":60,"name":"Cartoons","id":"431"}],"name":"TV","id":"164"}]}});