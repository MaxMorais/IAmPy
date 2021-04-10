
import os
import inspect
from .utils.observable import Observable, ODict
from . import errors, models as core_models
from .backends.sqlite import SQLiteDatabase

app = None

class Application(ODict):
    def __init__(self, is_server=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        global app
        app = self

        self.init_config()
        self.init_globals()
        self.init_db()
        self.load_all_meta()

        self.docs = Observable()
        self.events = Observable()
        self.is_server = is_server
        self.is_client = not self.is_server

    def init_db(self):
        self.db = SQLiteDatabase(self)
        self.db.connect()
        self.register_meta(core_models.models)
        self.db.migrate()

    def init_config(self):
        self.config = ODict(
            backend='sqlite',
            db=ODict(
                file = os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    'storage',
                    'iampy.db'
                ),
                connection_params=ODict(),
                dictrows = True,
                debug = False
            )
        )

    def init_globals(self):
        self.meta_cache = ODict()
        self.models = ODict()
        self.forms = ODict()
        self.views = ODict()
        self.flags = ODict()
        self.methods = ODict()
        
        # temp params while calling routes
        self.params = ODict()

    def register_lib(self, name, obj):
        # add standard libs and utils to iampy
        self[name] = obj

    def register_meta(self, models):
        # register models from app.model

        for doctype in models:
            self.meta_cache[doctype.name] = doctype
            self.models[doctype.name] = doctype
    
    def load_all_meta(self):
        for doc in self.db.get_all('DocType'):
            self.load_meta(doc.name)
            meta_definition = self.models[doc.name]
            if not meta_definition.name:
                raise errors.AssetionError(f'Name is mandatory for {doc.name}')
            
            if meta_definition.name != doc.name:
                raise errors.AssetionError(f'Model name mismatch for {doc.anem}: {meta_definition.name}')

            fieldnames = sorted(map(lambda df: df.fieldname, meta_definition.fields or []))
            duplicate_fieldnames = [x for x in fieldnames if fieldnames.count(name) > 0]

            if duplicate_fieldnames:
                raise errors.DuplicateFieldError(f'Duplicate fields in {doc.name}: {(", ".join(duplicate_fieldnames))}')

    def load_meta(self, meta):
        self.meta_cache[meta] = self.models[meta] = self.get_doc('DocType', meta)

    def get_models(self, filter_fn):
        models = self.models.values()
        return filter(filter_fn, models) if filter_fn else models

    def register_view(self, view, name, module):
        global views

        if view not in self.views:
            self.views[view] = {}
        self.views[view][name] = module

    def register_method(self, method, handler):
        self.methods[method] = handler

        if self.is_client:
            @self.post(f'/api/method/{method}')
            def async_handler(response):
                return response.json()

    def __call__(self, method, *args, **kwargs):
        if self.is_server:
            if method in self.methods:
                return self.methods[method](*args, **kwargs)
            else:
                raise iampy.errors.MethodNotFoundErrr(f'{method} not found')
        
        @self.app.post(f'/api/method/{method}', data={'args': args, 'kwargs': kwargs})
        def async_handler(response):
            return response.json()

    def add_to_cache(self, doc):
        if not self.docs:
            return

        # add to `app.docs` cache
        if doc.doctype and doc.name:
            if not doc.doctype in docs:
                self.docs[doc.doctype] = ODict()
            
            self.docs[doc.doctype][doc.name] = doc

            # Singles available as first level objects too
            if doc.doctype == doc.name:
                self.docs[doc.name] = doc

            # propagate change to `docs`
            doc.on('change', lambda docs=self.docs, **kwargs: docs.trigger('change', **kwargs))

    def remove_from_cache(self, doctype, name):
        if docs and doctype in self.docs and name in self.docs[doctype]:
            del self.docs[doctype][name]
    
    def is_dirty(self, doctype, name):
        return self.docs \
            and doctype in self.docs \
            and name in self.docs[doctype] \
            and self.docs[doctype][name]._dirty

    def get_doc_from_cache(self, doctype, name):
        if self.docs \
            and doctype in self.docs \
            and name in self.docs[doctype]:
            return self.docs[doctype][name]

    def get_meta(self, doctype):
        from iampy.model.meta import BaseMeta

        if self.meta_cache and doctype in self.meta_cache:
            model = self.models[doctype]

            if not model:
                raise Exception(f'{doctype} is not a registered doctype')
            
            meta_class = model.meta_class or BaseMeta
            self.meta_cache[doctype] = meta_class(model)
        
        return self.meta_cache[doctype]

    def get_doc(self, doctype, name):
        doc = self.get_doc_from_cache(doctype, name)

        if not doc:
            doc = self.get_document_class(doctype)(
                doctype = doctype,
                name = name
            )
            doc.load()
            self.add_to_cache(doc)
        
        return doc

    def get_document_class(self, doctype):
        from iampy.model.document import BaseDocument
        meta = self.get_meta(doctype)
        return document_class or BaseDocument

    def get_single(self, doctype):
        return self.get_doc(doctype, doctype)

        
    def get_duplicate(self, doc):
        new_doc = self.get_new_doc(doc.doctype)

        def mapper(d):
            o = ODict()
            o.update(d)
            o['name'] = ''
            return o

        for field in self.get_meta(doc.doctype).get_valid_fields():
            if field.fieldname in ('name', 'submitted'):
                continue

            if field.fieldtype == 'Table':
                new_doc[field.fieldname] = map(mapper, (doc[field.fieldname] or []))
            elif field.fieldtype == 'Form':
                new_doc[field.fieldname] = mapper(doc[field.fieldname] or {})
            else:
                new_doc[field.fieldname] = doc[field.fieldname]
            
        return new_doc

    def get_new_doc(self, doctype):
        doc = self.new_doc(doctype=doctype)
        doc._not_inserted = True
        doc.name = get_random_string()
        self.add_to_cache(doc)
        return doc
        
    def new_custom_doc(self, fields):
        from iampy.model.document import BaseDocument

        doc = BaseDocument({'is_custom': True, 'fields': fields})
        doc.name = get_random_string()
        self.add_to_cache(doc)
        return doc

    def create_meta(self, fields):
        from iampy.model.meta import BaseMeta
        return BaseMeta({'is_custom': True, 'fields': fields})

    def new_doc(self, data):
        doc = self.get_document_class(data.doctype)(data)
        doc.set_defaults()
        return doc
    
    def db_insert(self, data):
        return self.new_doc(data).db_insert()
        
    def sync_doc(self, data):
        if self.db.exist(data.doctype, data.name):
            doc = self.get_doc(data.doctype, data.name)
            doc.update(data)
            doc.db_update()
        else:
            self.db_insert(data)