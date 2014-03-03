/*jslint sloppy:true plusplus:true */
/*global window,document */

(function () {
	var typeMap = {
			channel: 'user',
			v: 'video',
			embed: 'video',
			list: 'playlist'
		},
		iframes,
		i,
		l;

	function importVideos(args) {
		var qs = ['locale={{ request.args.locale }}'], a;
		for (a in args) {
			if (args.hasOwnProperty(a)) {
				qs.push(a + '=' + args[a]);
			}
		}
		window.location.assign("{{ url_for('.index', _external=True) }}?" + qs.join('&'));
		return true;
	}

	function checkMatch(re, str) {
		var match = re.exec(str || window.location);
		if (match) {
			return importVideos({
				source: match[1],
				type: typeMap[match[2]] || match[2],
				id: match[3]
			});
		}
	}

	// Check if page url refers to youtube video:
	if (checkMatch(/(youtube)\.com\S*(v)=([\w\-]{11})/)) {
		return;
	}

	// Check if page url refers to youtube user/channel:
	if (checkMatch(/(youtube)\.com\/(user|channel)\/(\w+)/)) {
		return;
	}

	// Check if page url refers to youtube playlist:
	if (checkMatch(/(youtube)\.com\S*(list)=([\w\-]+)/)) {
		return;
	}

	// Else check the page for embedded video player:
	iframes = document.getElementsByTagName('iframe');
	for (i = 0, l = iframes.length; i < l; i++) {
		if (checkMatch(/(youtube)\.com\/(embed)\/([\w\-]{11})/, iframes[i].src)) {
			return;
		}
	}

	window.alert('No video found');
}());
