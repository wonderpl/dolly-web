<script>
	$(function () {
		$('#tags').select2({
			tags: function (query) {
				var result = {results: [], more: false};
				if (query && query.term) {
					if (query.term.length <= 2) {
						query.callback(result);
					} else {
						$.ajax({
							url: '{{ url_for("import.tags") }}',
							data: {
								prefix: query.term,
								size: 10,
								start: (query.page - 1) * 10
							},
						}).done(function (response) {
							$.each(response.tags || [], function() {
								result.results.push({id: this, text: this});
							});
							if (response.tags.length == 10) {
								result['more'] = true;
							}
							query.callback(result);
						});
					}
				}
			},
			containerCss: {width: '218px'},
		});
	});
</script>
