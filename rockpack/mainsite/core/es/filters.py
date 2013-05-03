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
            script = "doc['locale.{}.view_count'].value > doc['locale.{}.view_count'].value ? 1 : 0".format(entity.locale, el)
            filters.append(pyes.CustomFiltersScoreQuery.Filter(pyes.ScriptFilter(script=script), 5.0))
    return filters


def verified_channel_boost():
    return pyes.CustomFiltersScoreQuery.Filter(
        pyes.TermFilter(field='verified', value=True, boost=1.5)
    )


def editorial_boost():
    return pyes.CustomFiltersScoreQuery.Filter(
        pyes.TermFilter(script="_score * doc['editorial_boost'].value")
    )
