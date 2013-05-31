import re
from pkg_resources import resource_string
from wtforms.validators import ValidationError
from rockpack.mainsite.helpers import lazy_gettext as _


NAUGHTY_WORDS = dict((word, 1) for word in
                     resource_string(__name__, 'naughty_words.txt').split('\n'))
PUNCTUATION_RE = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
CAPITALIZED_SUBWORDS_RE = re.compile(r'[A-Z][^A-Z]*')


def naughty_word_validator(form, value):
    if not value.data:
        return
    words = PUNCTUATION_RE.split(value.data)
    if len(words) == 1 and not words[0].upper() == words[0]:
        words = CAPITALIZED_SUBWORDS_RE.findall(words[0][:1].upper() + words[0][1:])
    for word in words:
        if word and word.lower() in NAUGHTY_WORDS:
            raise ValidationError(_('Mind your language!'))
