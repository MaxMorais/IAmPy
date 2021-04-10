
from iampy import app
from .document import BaseDocument, ODict

class BaseMeta(BaseDocument):
    def __init__(self, data):
        if data.based_on:
            config = app.models[data.based_on]
            preserve = {
                'name': data.name,
                'label': data.label,
                'filters': data.filters
            }
            data.update(config)
            data.update(preserve)

        super().__init__(data)
        self.set_default_indicators()
        if self.setup_meta:
            self.setup_meta()
        
        if not self.title_field:
            self.title_field = 'name'
    
    def __setitem__(self, key, value):
        from iampy.utils.observable import Observable

        Observable.__setitem__(self, key, value)
        
    def update(self, data):
        self.update(data)
        self.process_fields()

    def process_fields(self):
        # add name field
        if not next(filter(lambda df: df.fieldname == 'name', self.fields)) and not self.is_single:
            self.fields = [
                ODict(
                    label = app._('ID'),
                    fieldname = 'name',
                    fieldtype = 'Data',
                    required = 1,
                    read_only = 1
                )
            ] + self.fields

        for field in self.fields:
            # name field is always required
            if df.fieldname == 'name':
                df.required = 1

            # attach default precision to Float and Currency
            if df.fieldtype in ('Float', 'Currency'):
                default_precision = app.SystemSettings.float_precision if app.SystemSettings else 2
                df.precision = df.precision or default_precision
        
    def has_field(self, fieldname):
        return bool(self.get_field(fieldname))

    def get_field(self, fieldname):
        if not hasattr(self, '_field_map'):
            self._field_map = {}
            for field in self.fields:
                self._field_map[field.fieldname] = field
        
        return self._field_map.get(fieldname)

    def get_fields_with(self, filters):
        def fn(df):
            match = True
            for key, value in filters.items():
                match = match and df[key] == value
            return match
        return list(filters(fn, self.fields))

    def get_label(self, fieldname):
        df = self.get_field()
        return df.get_label() if df and hasattr(df, 'get_label') else df.label if df else None
    
    def get_table_fields(self):
        if not self._table_fields:
            self._table_fields = self.get_fields_with({'fieldtype': 'Table'})
        return self._table_fields

    def get_form_fields(self):
        if not self._form_fields:
            self._form_fields = self.get_fields_with({'fieldtype': 'Form'})
        return self._get_form_fields

    def get_formula_fields(self):
        if not hasattr(self, '_formula_fields'):
            self._formula_fields = list(filter(lambda df: df.formula, self.fields))
        return self._formula_fields

    def has_formula(self):
        if not hasattr(self, '_has_formula'):
            self._has_formula = False
        
        if self.get_formula_fields():
            self._has_formula = True
        else:
            for tablefield in self.get_table_fields():
                if app.get_meta(tablefield.childtype).get_formula_fields():
                    self._has_formula = True
            
            for formfield in self.get_form_fields():
                if app.get_meta(form_field.childtype).get_formula_fields():
                    self._has_formula = True

        return self._has_formula

    def get_base_doctype(self):
        return self.get('based_on', self.name)
    
    def get_valid_fields(self, with_children=True):
        from iampy import model
        
        if not self.get('_valid_fields'):
            self._valid_fields = []
            self._valid_fields_with_children = []

        def _add(field, s = self):
            s._valid_fields.append(field)
            s._valid_fields_with_children.append(field)

        # fields validation
        for i, df in enumerate(self.fields, 1):
            if not df.fieldname:
                raise app.errors.ValidationError(
                    f'DocType {self.name}: "fieldname" is required at index {i}'
                )
            
            if not df.fieldtype:
                raise app.errors.ValidationError(
                    f'DocType {self.name}: "fieldtype" is required for field {df.fieldname}'
                )
        
        doctype_fields = map(lambda df: df.fieldname, self.fields)

        # standard fields
        for field in model.common_fields:
            if field.fieldtype in app.db.type_map \
                and field.fieldname not in doctype_fields:
                _add(field)
        
        if self.is_submittable:
            _add(ODict(
                fieldtype = 'Check',
                fieldname = 'submitted',
                label = app._('Submitted')
            ))

        if self.is_child:
            # child fields
            for field in model.child_fields:
                if field.fieldtype in app.db.type_map \
                    and field.fieldname not in doctype_fields:
                    _add(field)
        else:
            # parent fields
            for field in model.parent_fields:
                if field.fieldtype in app.db.type_map \
                    and field.fieldname not in doctype_fields:
                    _add(field)
        
        if self.is_tree:
            # tree fields
            for field in model.tree_fields:
                if field.fieldtype in app.db.type_map \
                    and field.fieldname not in doctype_fields:
                    _add(field)
        
        # doctype fields
        for field in self.fields:
            if field.fieldtype in app.db.type_map:
                _add(field)
            
            if field.fieldtype in ('Table', 'Form'):
                self._valid_fields_with_children.append(field)
        
        if with_children:
            return self._valid_fields_with_children
        else:
            return self._valid_fields

    def get_keyword_fields(self):
        if not self._keyword_fields:
            self._keyword_fields = self.keyword_fields

            if not (self._keyword_fields and self.fields):
                self._keyword_fields = map(lambda df: df.fieldname, 
                    filter(lambda df: df.fieldtype not in ('Form', 'Table') and df.required, self.fields))
            
            if not self._keyword_fields:
                self._keyword_fields = ['name']
        return self._keyword_fields

    def validate_select(self, field, value, errors, raise_errors):
        if not field.options:
            return
        
        if not field.required and value is None:
            return

        valid_values = field.options

        if isinstance(valid_values, str):
            valid_values = valid_values.split('\n')
        elif isinstance(valid_values, dict):
            valid_values = valid_values.items()
        
        if value not in valid_values:
            valid = ",".join(valid_values)
            if raise_errors:
                raise app.errors.ValueError(
                    f'DocType {self.name}: Invalid value "{value}" for "{field.label}". Must be one of {valid}'
                )
            else:
                errors[field.fieldname].append(f'Invalid value "{value}". Must be one of {valid}')
        return value

    def set_default_indicators(self):
        if not self.indicators:
            if self.is_submittable:
                self.indicators = {
                    'key': 'submitted',
                    'colors': {
                        0: indicator_color.GRAY,
                        1: indicator_color.BLUE
                    }
                }

    def get_indicator_color(self, doc):
        if app.is_dirty(self.name, doc.name):
            indicator_color.ORANGE
        else:
            if self.indicators:
                value = doc[self.indicators['key']]
                if value:
                    return self.indicators['colors'][value] or indicator_color.GRAY
                else:
                    return indicator_color.GRAY
            else:
                return indicator_color.GRAY

    def trigger(self, event, **params):
        params.update({'doc': self})
        super().trigger(event, **params)

    