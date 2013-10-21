<script>
	$(function () {
		$('#tags').select2({
			tags: true,
			minimumInputLength: 3,
			containerCss: {width: '218px'},
			ajax: {
				url: '{{ url_for("import.tags") }}',
				cache: true,
				quietMillis: 500,
				data: function (term, page) {
					return {prefix: term, size: 10, start: (page - 1) * 10};
				},
				results: function (data, page) {
					var result = {results: [], more: false};
					$.each(data.tags || [], function() {
						result.results.push({id: this, text: this});
					});
					if (data.tags.length == 10) {
						result['more'] = true;
					}
					return result;
				}
			},
			createSearchChoice: function (term) {
				return {id: term, text: term};
			},
			initSelection: function (element, callback) {
				var data = [];
				$(element.val().split(",")).each(function () {
					data.push({id: this, text: this});
				});
				callback(data);
			}
		});
	});
</script>
