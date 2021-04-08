
from iampy import Application
from iampy.backends.sqlite import SQLiteDatabase
from iampy.utils.observable import ODict
from bottle import route, run, request, response, PluginError
import json
import inspect


class IAmPyPlugin(object):
    name = 'iampy'
    api = 2

    def __init__(self, config, autocommit=True, dictrows=True, 
                 keyword='app', text_factory=str, functions=None,
                 aggregates=None, collations=None, extensions=None):

        self.config = config
        self.autocommit = autocommit
        self.dictrows = dict
        self.keyword = keyword
        self.text_factory = text_factory
        self.functions = functions or {}
        self.aggregates = aggregates or {}
        self.collations = collations or {}
        self.extensions = extensions or {}


    def setup(self, app):
        ''' Make sure that other installed plugins don't effect the same
        keyword argument.
        '''

        for other in app.plugins:
            if not isinstance(other, IAmPyPlugin):
                continue
            if other.keyword == self.keyword:
                raise PluginError('Foud another sqlite plugin with '
                                  'conflicting settings (non-unique keyword)')
            elif other.name == self.name:
                self.name = '_' + self.keyword
    
    def apply(self, callback, route):
        
        config = route.config
        _callback = route.callback

        argspec = inspect.getargspec(_callback)
        if keyword not in argspec.args:
            return callback

        g = lambda key, default: config.get('sqlite.' + key, default)

        dbfile = g('dbfile', self.dbfile)
        autocommit = g('autocommit', self.autocommit)
        dictrows = g('dictrows', self.dictrows)
        keyword = g('keyword', self.keyword)
        text_factory = g('text_factory', self.text_factory)
        functions = g('functions', self.functions)
        aggregates = g('aggregates', self.aggregates)
        collations = g('collations', self.collations)
        extensions = g('extensions', self.extensions)

        def wrapper(self, *args, **kwargs):

            db = app


@route('/api/resource/<doctype>')
def get_list(app, doctype):
    for key in ('fields', 'filters'):
        if key in request.query and if isinstance(request.query[key], str):
            request.query[key] = json.loads(request.query[key])

        return app.db.get_all(
            doctype = doctype,
            fields = request.query.fields,
            filters = request.query.filters,
            limit = request.query.limit or 20,
            offset = request.query.offset or 0,
            group_by = reques.query.group_by or '',
            order_by = request.query.order_by or 'creation',
            order = request.query.order or 'asc'
        )


@route('/api/resource/<doctype>/<name>')
def get_doc(app, doctype, name):
    doc = app.get_doc(doctype, name)
    return doc.get_valid_dict()


@route('/api/resource/<doctype>/<name>/<fieldname>')
def get_value(app, doctype, name, fieldname):
    return ODict(value = app.db.get_value(doctype, name, fieldname))


@route('/api/resource/<doctype>', 'POST')
def create(app, doctype):
    data = json.loads(request.body, object_pairs_hook=ODict)
    data.doctype = doctype
    doc = app.new_doc(data)
    doc.db_insert()
    app.db.commit()
    return doc.get_valid_dict()


@route('/api/resource/<doctype>/<name>', 'PUT')
def update(app, doctype, name):
    data = json.loads(request.body, object_pairs_hook=ODict)
    doc = app.get_doc(doctype, name)
    doc.update(data)
    doc.db_update()
    app.db.commit()
    return doc.get_valid_dict()


@route('/api/resource/<doctype>/<name>', 'DELETE')
def delete_one(app, doctype, name):
    app.db.delete_doc(doctype, name)
    app.db.commit()
    return {}


@route('/api/resource/<doctype>', 'DELETE')
def delete_many(app, doctype):
    names = json.loads(request.body or '[]')
    for name in names:
        app.db.delete_doc(doctype, name)
    app.db.commit()


@route('/api/resource/<doctype>/<name>', 'POST')
def upload_to_doc(app, doctype, name):
    tenant_dir = app.get_tenant_dir('uploads')
    file_docs = {}
    for name, content in request.files:
        content.save(tenant_dir, overwrite=True)

        doc = app.new_doc(ODict(
            doctype = 'File',
            name = 
        ))


@route('/api/upload/<doctype>/<name>/<fieldname>', 'POST')
def upload_to_field(app, doctype, name, fieldname):
    file_docs = upload(app, doctype, name)
    
