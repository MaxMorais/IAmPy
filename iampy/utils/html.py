from iampy import app
from iampy.utils.observable import ODict

try:
    from browser.template import Template
except ImportError as e:
    pass


def get_html(doctype, name):
    meta = app.get_meta(doctype)
    print_format = app.get_doc('PrintFormat', meta.print.print_format)

    doc = app.get_doc(doctype, name)
    context = ODict(
        doc = doc,
        app = app
    )

    try:
        html = Template(print_format.template).render(**context)
    except Exception as e:
        print(error)
        html = ''

    return '<div class="print-page">{}</div>'.format(html)
    