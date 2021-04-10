import math
import re
from numbers import Number
from .observable import ODict

number_formats = ODict({
    '#,###.##': ODict(
        fraction_sep='.',
        group_sep=',',
        precision=2
    ),
    '#.###,##': ODict(
        fraction_sep=',',
        group_sep='.',
        precision=2
    ),
    '# ###.##': ODict(
        fraction_sep='.',
        group_sep=' ',
        precision= 2
    ),
    '# ###,##': ODict(
        fraction_sep=',',
        group_sep=' ',
        precision=2
    ),
    "#'###.##": ODict(
        fraction_sep='.',
        group_sep="'",
        precision=2
    ),
    '#, ###.##': ODict(
        fraction_sep='.',
        group_sep=', ',
        precision=2
    ),
    '#,##,###.##': ODict(
        fraction_sep='.',
        group_sep=',',
        precision= 2
    ),
    '#,###.###': ODict(
        fraction_sep='.',
        group_sep=',',
        precision=3
    ),
    '#.###': ODict(
        fraction_sep='',
        group_sep='.',
        precision=0
    ),
    '#,###': ODict(
        fraction_sep='',
        group_sep=',',
        precision=0
    )
})

def parse_number(number, format="#,###.##"):
    if not number: return 0

    if not isinstance(number, Number):
        return number

    info = get_format_info(format)
    return parse_float(remove_separator(number, info.group_sep))


def format_number(number, format="#,###.##", precision=None):
    if not number: return 0

    info = get_format_info(format)
    if not precision: precision = info.precision

    number = parse_number(number)
    is_negative = number < 0

    number = abs(number)
    parts = "{:.{1}f}".format(number, precision).split(".")

    # get group position and parts
    group_position = 3 if info.group_sep else 0
    if group_position:
        integer = parts[0]

        s = ''
        for i in range(len(integer)):
            l = len(remove_separator(s, info.group_sep))
            if format == "#,##,###.##" and "," in s:
                # INR
                group_position = 2
                l += 1

            s += integer[i]

            if l and not ((l + 1) % group_position) and i != 0:
                s += info.group_sep

        parts[0] = "".join(reversed(s.split('')))

    if not parts[0]:
        parts[0] = "0"

    # join decimal
    parts[1] = info.fraction_sep + parts[1] if info.fraction_sep and parts[1] else ''

    # join
    return ("-" if is_negative else "") + parts[0] + parts[1]
    

def get_format_info(format):
    format_info = number_formats.get(format)

    if not format_info:
        raise ValueError(f'Unknown number format "{format}"')

    return format_info


def round(num, precision):
    is_negative = num < 0
    d = int(precision or 0)
    m = math.pow(10, d)
    n = float("{:.8f}".format((abs(num) * m) if d else abs(num)))  # Avoid rounding errors
    i = math.floor(n)
    f = n - i
    r = (i if i % 2 == 0 else i + 1) if not precision and f == 0.5 else math.round(n)
    r = r / m if d else r
    return - r if is_negative else r
    

def remove_separator(text, sep):
    return re.sub(r'\\.' if sep == '.' else sep, '', text)
