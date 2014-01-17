(function(w,d){

	var _ = {},
		toggled = false

	_.init = function () {
		$(d).on('click', 'a.nav-toggle', _.toggleNav);
	};

	_.toggleNav = function () {
		if ( toggled === true ) {
			d.getElementById('header').className = '';
			d.body.className = '';
			toggled = false;
		} else {
			d.getElementById('header').className = 'toggled';
			d.body.className = 'toggled';
			toggled = true;
		}
	};

	$(function() {
		console.log('initalised');
		_.init();
	});

})(window,document);