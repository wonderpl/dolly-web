<script>
$(function () {
    var categoryField = $('#category'),
userField = $('#user'),
channelField = $('#channel'),
videoField = $('#video_rel');
if (userField.length === 0) {
    userField = $('#owner_rel');
}
if (channelField.length === 0) {
    channelField = $('#channel_rel');
}

function dataToResults (data, page) {
    var results = $.map(data, function (text, id) {
        return {id:id, text:text};
    });
    return {results: results};
}

userField.select2({
    _placeholder: 'Search for user',
    minimumInputLength: 3,
    minimumResultsForSearch: 10,
    ajax: {
        url: '{{ url_for("import.users") }}',
    data: function (term, page) {
        return {prefix: term};
    },
    results: dataToResults
    },
    initSelection: function(element, callback) {
        $.ajax('{{ url_for("import.users") }}', {
            data: {
                exact_name: userField.select2("val"),
            },
        }).done(function(data) {
            var r = dataToResults(data)['results'][0];
            callback(r); 
            userField[0].value = r['id'];
        });
    },
    width: 'element',
    dropdownCssClass: 'bigdrop'
}).on('change', function (e) {
    channelField.select2('data', {});
});

videoField.select2({
    _placeholder: 'Search for video',
    minimumInputLength: 10,
    ajax: {
        url: '{{ url_for("import.videos") }}',
    data: function (term, page) {
        return {vid: term};
    },
    results: dataToResults
    },
    initSelection: function(element, callback) {
        $.ajax('{{ url_for("import.videos") }}', {
            data: {
                instance_id: decodeURI(window.location.search.substring(1)).split('=').slice(-1)[0],
            },
        }).done(function(data) {
            var r = dataToResults(data)['results'][0];
            callback(r);
            videoField[0].value = r['id'];
        });
    },
    width: 'element',
    dropdownCssClass: 'bigdrop'
});

channelField.select2({
    quietMillis: 1000,
    minimumInputLength: 4,
    ajax: {
        url: '{{ url_for("import.channels") }}',
    data: function (term, page) {
        return {prefix: term};
    },
    results: dataToResults
    },
    initSelection: function(element, callback) {
        $.ajax('{{ url_for("import.channels") }}', {
            data: {
                exact_name: channelField.select2("val"),
            },
        }).done(function(data) {
            var r = dataToResults(data)['results'][0];
            callback(dataToResults(data)['results'][0]); 
            channelField[0].value = r['id'];
        });
    },
    //createSearchChoice: function (term) {
    //    return {
    //        id: '_new:' + term,
    //        text: term + ' <span class="add-new">create new</span>'
    //    };
    //},
    width: 'element',
    dropdownCssClass: 'bigdrop'
});
categoryField.select2('focus');
});
</script>
