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

		$('input#filter').change(function () {
			var input = $(this),
				form = input.closest('form'),
			    group = input.closest('.control-group'),
			    info = input.next('.help-block');
			$.post('{{ url_for("broadcast_message.check_filter") }}', form.serialize())
				.done(function (result) {
					group.toggleClass('error', false);
					info.html('Matching users: ' + result.user_count);
				})
				.fail(function (xhr) {
					var result = $.parseJSON(xhr.responseText)
					group.toggleClass('error', true);
					info.html(result.error);
				});
		}).after('<span class="help-block">');
	});
</script>
