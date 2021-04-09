
from iampy import app

from datetime import datetime

from . import name
from ..utils.observable import Observable, ODict
from ..utils.number_format import round
from typing import Iterable


class BaseDocument(Observable):
    def __init__(self, data):
        super().__init__()
        self.fetch_values_cache = {}
        self.flags = ODict()
        self.setup()
        self.update()

    def setup(self):
        pass

    def update(self, data):
        for fieldname, value in data.items():
            value = data[fieldname]
            if fieldname.startswith('_'):
                self[fieldname] = value
            elif isinstance(value, dict):
                self[fieldname] = value
            elif isinstance(value, Iterable):
                self.extend(value)
    
    @property
    def meta(self):
        if self.is_custom:
            self._meta = app.create_meta(self.fields)
        if not getattr(self, '_meta'):
            self._meta = app.get_meta(self.doctype)
        return self._meta

    @property
    def get_settings(self):
        if not hasattr(self, '_settings'):
            self._settings = app.get_single(self.meta.settings)
        return self._settings

    def __setitem__(self, fieldname, value):
        if self[fieldname] != value:
            self._dirty = True
            # if child is dirty, parent is dirty too
                self.parentdoc._dirty = True

            old = self[fieldname]
            if isinstance(value, Iterable) and not isinstance(value, dict):
                self[fieldname] = []
                for i, row in enumerate(value, 1):
                    row.idx = i
                    self.append(fieldname, row, trigger=False)
            else:
                self.validate_field(fieldname, value)
                self.trigger('before_change',
                    doc = self,
                    fieldname = fieldname,
                    old_value = old
                )
                self[fieldname] = value

            # always run apply_change from the parentdoc
            if self.meta.is_child and self.parentdoc:
                self.parentdoc.apply_change(self.parentfield, old)
            else:
                self.apply_change(fieldname, old)
            
    
    def apply_change(self, fieldname, old):
        self.apply_formula(fieldname)
        self.round_floats()
        self.trigger('after_change', 
            doc = self,
            fieldname = fieldname,
            old_value = old,
            new_value = self[fieldname]
        )

    def set_defaults(self):
        for field in self.meta.fields:
            if self[field.fieldname] is None:
                default = None

                if field.fieldtype == 'Table':
                    default = []
                elif field.fieldtype == 'Form':
                    default = {}
                if callable(field.default):
                    default = field.default(self)
                else:
                    default = field.default
            
                self[field.fieldname] = default
        
        if self.meta.based_on and self.meta.filters:
            self.set_values(self.meta.filters)

    def cast_values(self):
        for field in self.meta.fields:
            if self[field.fieldname] is None:
                continue

            if field.fieldtype in ('Int', 'Check'):
                value = int(value, 10)
            elif field.fieldtype in ('Float', 'Currency', 'Percent'):
                value = float(value)
            self[field.fieldname] = value

    def set_keywords(self):
        self.keywords = ",".join([
            self[fieldname] for fieldname in self.meta.get_keyword_fields()
        ])

    def append(self, key, document = {}, trigger=True)
        if not self[key]:
            self[key] = []

        self[key].append(self._init_child(document, key))
        
        if trigger:
            self._dirty = True
            self.apply_change(key)

    def _init_child(self, data, key):
        if isinstance(data, BaseDocument):
            return data

        data.update({
            'doctype': self.meta.get_field(key).childtype,
            'parent': self.name,
            'parenttype': self.doctype,
            'parentfield': key,
            'parentdoc': self
        })

        if 'idx' not in data:
            data.idx = len(self.get(key, []))
        
        if 'name' not in data:
            data['name'] = app.get_random_string()

        return BaseDocument(data)

    def validate(self):
        errors = ODict()
        self.validate_insert(errors, False)
        return bool(not errors), errors

    def validate_insert(self, errors=None, raise_errors=True):
        if errors is None: errors = ODict()
        self.validatet_mandatory(errors, raise_errors)
        self.validate_fields(errors, raise_errors)

    def validate_mandatory(self, errors, raise_errors):
        check_for_mandatory = [self]
        children_fields = filter(lambda df: df.fieldtype in ('Table', 'Form'))
        for children_field in children_fields:
            if isinstance(self[children_field.fieldname], dict):
                check_for_mandatory.append(self[children_field.fieldname])
            else:
                check_for_mandatory.extend(self[children_field.fieldname])
        
        def get_missing_mandatory(doc):
            def is_empty(df):
                value = doc.get(df.fieldname)
                if isinstance(df.fieldtype, 'Table') and not value:
                    return True
                elif isinstance(df.fieldtype 'Form') and not value:
                    return True
                elif value is None or value == '':
                    return True

            mandatory_fields = filter(lambda df: df.required, doc.meta.fields)
            message = ', '.join(map(lambda df: f'"{df.label}"', filter(is_empty, mandatory_fields)))

            for field in filter(is_empty, mandatory_fields):
                if field.fieldname not in errors:
                    errors[field.fieldname] = []
                if not doc.meta.is_child:
                    errors[field.fieldname].append('Is mandatory')
                else:
                    errors[field.fieldname].append('On Row {}: Is Mandatory'.format(doc.idx))

            if message and doc.meta.is_child:
                parentfield = doc.parentdoc.meta.get_field(doc.parentfield)
                message = f'{parentfield.label}: Row {doc.idx}: {message}'
            
            return message
        
        missing_mandatory = list(filter(None, map(get_missing_mandatory, check_for_mandatory)))

        if missing_mandatory and raise_errors:
            fields = '\n'.join(missing_mandatory)
            message = app._('Value missing for {0}', fields)
            raise iampy.errors.MandatoryError(message)

    def validate_fields(self, errors, raise_errors):
        for field in self.meta.fields:
            errors.setdefault(field.fieldname, [])
            self.validate_field(field.fieldname, self[field.fieldname], errors, raise_errors)

    def validate_field(self, fieldname, value, errors, raise_errors):
        field = self.meta.get_field(fieldname)

        if not field:
            raise iampy.errors.InvalidFieldError(f'Invalid field "{fieldname}"')
        
        if field.fieldtype == 'Select':
            self.meta.validate_select(field, value, errors, raise_errors)
        if field.validate and value not is None:
            validator = None
            if isinstance(field.validate, dict):
                validator = self.get_validate_function(field.validate)
            elif callable(field.validate):
                validator = field.validate
            if validator:
                try:
                    validator(value, self)
                except Exception as e:
                    if raise_errors:
                        raise e
                    errors[field.fieldname].append(e.message)
        
    def get_validate_function(self, validator):
        # TODO: need work
        pass

    def get_valid_dict(self):
        data = {}
        for field in self.meta.get_valid_fields():
            value = self[field.fieldname]
            if isinstance(value, dict) and hasattr(value, 'get_valid_dict'):
                value = get_valid_dict()
            elif isinstance(value, Iterable):
                value = map(lambda doc: doc.get_valid_dict() if hasattr(doc, 'get_valid_dict') else doc)
            data[field.fieldname] = value
        return data

    def set_standard_values(self):
        # set standard values on server-side only
        if app.is_server:
            if self.is_submittable and self.submitted is None:
                self.submitted = 0
            
        now = datetime()
        if not self.owner:
            self.owner = app.session.user

        if not self.creation:
            self.creation = now
        
        self.update_modified()

    def update_modified(self):
        if app.is_server:
            now = datetime.now()
            self.modified_by = app.session.user
            self.modified = now

    def load(self):
        data = app.db.get(self.doctype, self.name)
        if data and data.name:
            self.sync_values(data)
            if self.meta.is_single:
                self.set_defaults()
                self.cast_values()
            self.load_links()
        else:
            raise frappe.errors.NotFoundError(f'Not Found: {self.doctype}: {self.name}')
    
    def load_links(self):
        self._links = {}
        for df in filter(lambda df: df.inline):
            self.load_link(df.fieldname)
    
    def load_link(self, fieldname):
        df = self.meta.get_field(fieldname)
        if self[df.fieldname]:
            self._links[df.fieldname] = app.get_doc(
                df.target,
                self[df.fieldname]
            )
    
    def get_link(self, fieldname):
        return self._links.get(fieldname, None)

    def sync_values(self, data):
        self.clear_values()
        self.trigger('before_sync', doc=self)
        self.set_values()
        self._dirty = False
        self.trigger('after_sync', doc=self)

    def clear_values(self):
        to_clear = ['_dirty', '_not_inserted'] + map(
            lambda df: df.fieldname,
            self.meta.get_valid_fields())
        for key in to_clear:
            self[key] = None

    def set_child_idx(self):
        # renumber children
        for field in self.meta.get_valid_fields():
            if field.fieldtype == 'Form':
                self[field].idx = 1
            elif field.fieldtype == 'Table':
                for i, row in enumerate(self[field.fieldtype], 1):
                    row.idx = i
    
    def compare_with_current_doc(self):
        if app.is_server and not self.is_new():
            current_doc = self.db.get(self.doctype, self.name)

            # Check for conflict
            if current_doc and self.modified != current_doc.modified:
                raise iampy.errors.Conflict(
                    app._('Document {0} {1} has been modified after loading', [
                        self.doctype,
                        self.name
                    ])
                )
            
            # set submit action flag
            if self.submitted and not current_doc.submitted:
                self.flags.submit_action = True

            if current_doc.submitted and not self.submitted:
                self.flags.revert_action = True

    def apply_formula(self, fieldname):
        if not self.meta.has_formula():
            return False
        
        doc = self
        changed = False

        def should_apply_formula(field, doc):
            if field.read_only:
                return True
            if field.fieldame and field.formula_depends_on and field.fieldname in field.formula_depends_on:
                return True
            if not app.is_server:
                if doc[field.fieldname] in (None, ''):
                    return True
            return False

        # form children
        for formfield in self.meta.get_form_fields():
            formula_fields = app.get_meta(formfield.childype).get_formula_fields()

            if formula_fields:
                row = self[formfield.fieldname] or {}
                for field in formula_fields:
                    if should_apply_formula(field, row):
                        val = self.get_value_from_formula(field, row)
                        previous_val = row[field.fieldname]
                        if val not is None and previous_val != val:
                            row[field.fieldname] = val
                            changed = True

        # table children
        for tablefield in self.meta.get_table_fields():
            formula_fields = app.get_meta(tablefield.childtype).get_formula_fields()

            if formula_fields:
                # for each row
                for row in (self[tablefield.fieldname] or []):
                    for field in formula_fields:
                        if should_apply_formula(field, row):
                            val = self.get_value_from_formula(field, row)
                            previous_val = row[field.fieldname]
                            if val not is None and previous_val != val:
                                row[field.fieldname] = val
                                changed = True

        # parent or child row
        for field in self.meta.get_formula_fields():
            if should_apply_formula(field, doc):
                previous_val = doc[field.fieldname]
                val = self.get_value_from_formula(field, doc)
                if val not is None and previous_val != val:
                    doc[field.fieldname] = value
                    changed = True
        
        return changed

    def get_value_from_formula(self, field, doc):
        value = None

        if doc.meta.is_child:
            value = field.formula(doc, doc.parentdoc)
        else:
            value = field.formula(doc)

        if value is None:
            return

        if field.fieldtype in ('Float', 'Currency'):
            value = self.round(value, field)
        
        if field.fieldtype == 'Form':
            doc = self._init_child(doc, field.fieldname)
            doc.round_floats()
        elif field.fieldtype == 'Table':
            def doc_round_floats(row):
                doc = self._init_child(row, field.fieldname)
                doc.round_floats()
                return doc
            
            value = map(doc_round_floats, value)
        
        return value

    def set_name(self):
        naming.set_name(self)

    def db_commit(self):
        # re-run triggers
        self.set_keywords()
        self.set_child_idx()
        self.apply_formula()
        self.trigger('validate')

    def db_insert(self):
        self.set_name()
        self.set_standard_values()
        self.commit()
        self.validate_insert()
        self.trigger('before_insert')

        old_name = self.name
        data = app.db.insert(self.doctype, self.get_valid_dict())
        self.sync_values(data)

        if old_name != self.name:
            app.remove_from_cache(self.doctype, old_name)

        self.trigger('after_insert')
        self.trigger('after_save')

    def db_update(**kwargs):
        if kwargs:
            self.update(kwargs)
        self.compare_with_current_doc()
        self.commit()
        self.trigger('before_update')

        # before submit
        if self.flags.submit_action: self.trigger('before_submit')
        if self.flags.revert_action: self.trigger('before_rever')

        # update modified by and modified
        self.update_modified()

        data = self.db.update(self.doctype, self.get_valid_dict())
        self.sync_values(data)

        self.trigger('after_update')
        self.trigger('after_save')

        # after submit
        if self.flags.submit_action: self.trigger('after_submit')
        if self.flags.revert_action: self.trigger('after_revert')
    
    def db_delete(self):
        self.trigger('before_delete')
        app.db.delete(self.doctype, self.name)
        self.trigger('after_delete')

    def save(self):
        if self._not_inserted:
            return self.db_insert()
        else:
            return self.db_update()

    def delete(self):
        self.db_delete()

    def submit(self):
        self.submitted = 1
        self.db_update()

    def revert(self):
        self.submitted = 0
        self.db_update()

    def rename(self, new_name):
        self.trigger('before_rename')
        app.db.rename(self.doctype, self.name, new_name)
        self.name = new_name
        self.trigger('after_rename')

    def trigger(self, event, **pargs):
        if self[event]:
            self[event](**params)
        self.trigger(event, **params)

    def get_sum(self, tablefield, childfield):
        return reduce(
            lambda a, b: a + b, 
            map(lambda d: float(d[childfield] or 0), self[tablefield] or []), 0)
    
    def get_from(self, doctype, name, fieldame):
        if not name: return None
        return app.db.get_cached_value(docype, name, fieldname)
    
    def round(self, df = None):
        if isinstance(df, string):
            df = self.meta.get_field(df)
        
        system_precision = app.SystemSettings.float_precision
        default_precision = system_precision if system_precision else 2
        precision = df.precision if df and df.precision not is None else default_precision
        return round(value, precision)

    def is_new(self):
        return self._not_inserted 