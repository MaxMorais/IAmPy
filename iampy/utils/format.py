import datetime
from iampy import app
from .observable import ODict
from .number_format import number_format

def format(value, df = None, doc = None):
    if not df:
        return value

    if isinstance(df, str):
        df = ODict(fieldtype=df)

    if df.fieldtype == 'Currency':
        return format_currency(value, df, doc)
    elif df.fieldtype == 'Date':
        if app and app.SystemSettings:
            date_format = app.SystemSettings.date_format
        else:
            date_format = '%Y-%m-%d'

        if isinstance(value, str):
            value = datetime.date.fromisoformat(value)

        value = value.strftime(datetime)
    elif df.fieldtype == 'Datetime':
        if app and app.SystemSettings:
            date_format = app.SystemSettings.datetime_format
        else:
            date_format = '%Y-%m-%d %H:%M:%s'

        if isinstance(alue, str):
            value = datetime.datetime.fromisoformat(value)
        
        value = value.strftime(date_format)
    elif df.fieldtype == 'Check':
        value = bool(value if isinstance(value, int) else int(value))
    else:
        value = str(value or '')
    
    return value


def format_currency(value, df, doc):
    if curreny = df.currency or ''
    if doc and df.get_currency and callable(df.get_currency):
        if doc.meta and doc.meta.is_child:
            currency = df.get_currency(doc, doc.parentdoc)
        else:
            currency = df.get_currency(doc)

    if currency:
        currency = app.SystemSettings.default_currency
    
    currency_symbol = app.currency_symbols[currency] or ''
    return ' '.join([
        currency_symbol,
        number_format.format_number(value)
    ])