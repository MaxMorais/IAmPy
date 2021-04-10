from iampy import app
from iampy.utils import get_random_string

def set_name(doc):
    if app.is_server:
        # if is server, always name again if autoincrement or other
        if doc.meta.naming == 'autoincrement':
            doc.name = get_next_id(doc.doctype)
            return

        if doc.meta.settings:
            number_series = doc.get_settings().number_series
            if number_series:
                doc.name = get_series_next(number_series)
        
    if doc.name:
        return

    # name == doctype for Single
    if doc.meta.is_single:
        doc.name = doc.meta.name
        return

    # assign a random name by default
    # override doc to set a name
    if not doc.name:
        doc.name = get_random_string()


def get_next_id(doctype):
    # get the last inserted row

    last_inserted = get_last_inserted(doctype)
    name = 1
    if last_inserted:
        try:
            last_number = int(last_inserted.name)
        except:
            last_number = 0
        last_number += 1
    
    return f'{name:09}'


def get_last_inserted(doctype):
    last_inserted = app.db.get_all(
        doctype = doctype,
        fields = [name],
        limit = 1,
        order_by = 'creation',
        order = 'desc'
    )
    return last_inserted[0] if last_inserted else None


def get_series_next(prefix):
    if not app.db.exists('NumberSeries', prefix):
        create_number_series(prefix)
        series = app.get_doc('NumberSeries', prefix)
    nxt = series.next()
    return ''.join([prefix, nxt])


def create_number_series(prefix, setting = None, start=1000):
    if not app.db.exists('NumberSeries', prefix):
        series = app.new_doc(
            doctype = 'NumberSeries',
            name = prefix,
            current = start
        )
        series.db_insert()

        if setting:
            setting_doc = app.get_single(setting)
            setting_doc.number_series = series.name
            setting_doc.db_update()
