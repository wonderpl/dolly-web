import re
from pkg_resources import resource_string
from wtforms.validators import ValidationError
from rockpack.mainsite.helpers import lazy_gettext as _


NAUGHTY_WORDS = dict((word, 1) for word in
                     resource_string(__name__, 'naughty_words.txt').split('\n'))
CAPITALIZED_SUBWORDS_RE = re.compile('[A-Z][^A-Z]*')


def naughty_word_validator(form, value):
    words = value.data.split()
    if len(words) == 1:
        words = CAPITALIZED_SUBWORDS_RE.findall(value.data[:1].upper() + value.data[1:])
    for word in words:
        if word.lower() in NAUGHTY_WORDS:
            raise ValidationError(_('Mind your language!'))
