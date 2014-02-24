(function(w,d){

	var _ = {},
		toggled = false

	_.init = function () {
		$(d).on('click', 'a.nav-toggle', _.toggleNav);
		_.validatePassword();
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

	_.validatePassword = function() {

		$(d).on('submit', '#resetform', function(e){
			if ( $('#password').val().length > 6 && $('#password2').val().length > 6 ) {
				if ( $('#password').val() !== $('#password2').val() ) {
					e.preventDefault();
					$('h2').addClass('error');
					$('h2 span').html('Passwords must match.')
				}
			} else {
				e.preventDefault();
				$('h2').addClass('error');
				$('h2 span').html('Passwords must be at least 6 characters long.')
			}
		});
	};

	$(function() {
		_.init();
	});

})(window,document);