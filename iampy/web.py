
import sys
import os

sys.path.insert(0, os.path.join(
    os.path.abspath(
        os.path.dirname(__file__)
    ),
    '..'
))

from iampy import get_application
from iampy.backends.sqlite import SQLiteDatabase, sqlite3
from iampy.utils.observable import ODict
from bottle import route, run, request, response, PluginError
import json
import bottle
import inspect
import sqlite3


class IAmPyPlugin(object):
    name = 'iampy'
    api = 2

    def __init__(self, keyword='app'):
        self.keyword = keyword

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
        _callback = route.callback

        argspec = inspect.getargspec(_callback)
        if self.keyword not in argspec.args:
            return callback
        
        def wrapper(*args, **kwargs):
            app = get_application()

            kwargs[self.keyword] = app
            request_writable = bottle.request.method in ('POST', 'PUT', 'DELETE')

            try:
                if request_writable and app.config.db.autocommit:
                    app.db.begin()

                rv = callback(*args, **kwargs)
                
                if request_writable and app.config.db.autocommit:
                    app.db.commit()
            except sqlite3.IntegrityError as e:
                if request_writable and app.config.db.autocommit:
                    app.db.rollback()
                raise bottle.HTTPError(500, 'Database Error', e)
            except bottle.HTTPError as e:
                if request_writable and app.config.db.autocommit:
                    app.db.commit()
                raise e
            finally:
                app.db.close()

            if getattr(callback, 'as_json', False):
                bottle.response.headers['Content-Type'] = 'application/json'
                bottle.response.headers['Cache-Control'] = 'no-cache'
                rv = json.dumps(rv)

            return rv

        # Replace the route callback with the wrapped one.
        return wrapper


def rjson(fn):
    fn.as_json = True
    return fn


@route('/api/resource/<doctype>')
@rjson
def get_list(doctype, app):
    for key in ('fields', 'filters'):
        if key in request.query and isinstance(request.query[key], str):
            request.query[key] = json.loads(request.query[key])

        return app.db.get_all(
            doctype = doctype,
            fields = request.query.fields,
            filters = request.query.filters,
            limit = request.query.limit or 20,
            offset = request.query.offset or 0,
            group_by = request.query.group_by or '',
            order_by = request.query.order_by or 'creation',
            order = request.query.order or 'asc'
        )
   

@route('/api/resource/<doctype>/<name>')
@rjson
def get_doc(doctype, name, app):
    doc = app.get_doc(doctype, name)
    return doc.get_valid_dict()


@route('/api/resource/<doctype>/<name>/<fieldname>')
@rjson
def get_value(doctype, name, fieldname, app):
    return ODict(**{name : app.db.get_value(doctype, name, fieldname)})


@route('/api/resource/<doctype>', 'POST')
@rjson
def create(doctype, app):
    data = json.loads(request.body, object_pairs_hook=ODict)
    data.doctype = doctype
    doc = app.new_doc(data)

    errors = doc.get_errors()
    if not errors:
        return {
            'status': -1,
            'msg': errors
        }
    else:
        doc.db_insert()
        return {
            'status': 0,
            'id': doc.name
        }


@route('/api/resource/<doctype>/search', 'POST')
@rjson
def search(doctype, app):
    pass

@route('/api/resource/<doctype>/<name>', 'PUT')
@rjson
def update(doctype, name, app):
    data = json.loads(request.body, object_pairs_hook=ODict)
    doc = app.get_doc(doctype, name)
    doc.update(data)
    doc.db_update()
    return doc.get_valid_dict()


@route('/api/resource/<doctype>/<name>', 'DELETE')
@rjson
def delete_one(doctype, name, app):
    app.db.delete_doc(doctype, name)
    return {}


@route('/api/resource/<doctype>', 'DELETE')
@rjson
def delete_many(doctype, app):
    names = json.loads(request.body or '[]')
    for name in names:
        app.db.delete_doc(doctype, name)
    return {}


@route('/api/resource/<doctype>/<name>', 'POST')
@rjson
def upload_to_doc(doctype, name, app):
    tenant_dir = app.get_tenant_dir('uploads')
    file_docs = {}
    for name, content in request.files:
        content.save(tenant_dir, overwrite=True)

        doc = app.new_doc(ODict(
            doctype = 'File',
        #    name = 
        ))


@route('/api/upload/<doctype>/<name>/<fieldname>', 'POST')
@rjson
def upload_to_field(doctype, name, fieldname, app):
    file_docs = upload(app, doctype, name)
    

if __name__ == '__main__':
    app = bottle.default_app()
    app.install(IAmPyPlugin())
    bottle.run(host='127.0.0.1', port=8080, debug=True)