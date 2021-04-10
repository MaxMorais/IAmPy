
import random
import unicodedata
import re
import string


def slug(text):
    _slug_strip_re = re.compile(r'[^\w\s-]')
    _slug_hyphenate_re = re.compile(r'[-\s]+')

    value = unicodedata.normalize('NFKD', text)
    value = _slug_strip_re.sub('', value).lower()
    return _slug_hyphenate_re.sub('-', value)


def get_random_string():
    return "".join([
        random.choice(string.ascii_letters + string.digits)
        for i in range(10)
    ])


def unique(lst, key=lambda it: it):
    return list(set(map(key, lst)))


def duplicate(lst, key=lambda it: it):
    return [item for item in unique(lst, key) if lst.count(item) > 1]