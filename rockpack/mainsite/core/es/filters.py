import pyes
from rockpack.mainsite import app


def locale_filter(entity):
    """ Prioritises results for a given locale.

        For the current locale, apply a boost factor where the view_count
        is higher than another locale. This should result in relevant documents
        for this locale rising to the top (showing all results, but prioritising
        this locale).

        Accepts `entity` argument
        Expects `entity.locale` to be available (a string)
        """
    if not entity.locale:
        return None

    filters = []
    for el in app.config.get('ENABLED_LOCALES'):
        if entity.locale != el:
            # NOTE: This might get unwieldy for a large number of locales,
            # Need to find a better way of doing this
            script = "doc['locales.{}.view_count'].value < doc['locales.{}.view_count'].value ? 1 : 0".format(entity.locale, el)
            filters.append(pyes.CustomFiltersScoreQuery.Filter(pyes.ScriptFilter(script=script), 0.0001))
    return filters


def negatively_boost_favourites():
    return pyes.CustomFiltersScoreQuery.Filter(
        pyes.TermFilter(field='favourite', value=True),
        boost=app.config.get('FAVOURITES_NEGATIVE_BOOST', 0.0000001))


def verified_channel_boost():
    return pyes.CustomFiltersScoreQuery.Filter(
        pyes.TermFilter(field='verified', value=True),
        boost=app.config.get('VERIFIED_BOOST', 1.5)
    )


def boost_from_field_value(field, reduction_factor=1):
    script = "(doc['{}'].value + 1.0) / {}".format(field, reduction_factor)
    return pyes.CustomFiltersScoreQuery.Filter(pyes.MatchAllFilter(), script=script)


def boost_by_time():
    script = "(0.08 * ((3.16*pow(10,-11)) * doc['{}'].value) + 0.05) + 1.0".format('date_added')
    return pyes.CustomFiltersScoreQuery.Filter(pyes.MatchAllFilter(), script=script)
