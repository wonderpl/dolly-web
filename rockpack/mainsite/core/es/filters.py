import time
import datetime
import pyes
from rockpack.mainsite import app


def locale_filter(entity):
    """ Prioritises results for a given locale.

        Accepts `entity` argument
        Expects `entity.locale` to be available (a string)
        """
    if not entity.locale:
        return None

    script = "(doc['locales.{}.view_count'].value / (doc['date_added'].date.getMillis() * 3600000)) + 1".format(entity.locale)
    return pyes.CustomFiltersScoreQuery.Filter(pyes.MatchAllFilter(), script=script)


def country_restriction(country):
    script = """(
        doc['country_restriction.allow'].value == null ? 1 : (doc['country_restriction.allow'].value.contains('{country}') ? 1 : 0)
        ) &
    (
    doc['country_restriction.deny'].value == null ? 1 : (doc['country_restriction.deny'].value.contains('{country}') ? 1 : 0)
    )""".format(country=country)  # % both  #.format(rel=relationship, country=country, condition=condition)
    return pyes.ScriptFilter(script)


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
    script = "(0.05 * ((3.16*pow(10,-19)) * doc['{}'].date.getMillis()) + 0.09) + 1.0".format('date_added')
    return pyes.CustomFiltersScoreQuery.Filter(pyes.MatchAllFilter(), script=script)


def channel_rank_boost(locale):
    script = "doc['normalised_rank.%s'].value + 1.0" % locale
    return pyes.CustomFiltersScoreQuery.Filter(pyes.MatchAllFilter(), script=script)
