from iampy import app
from iampy.utils.observable import Observable, ODict
from iampy.utils.cache import CacheManager
from iampy.utils import get_random_string


class Database(Observable):
    def __init__(self):
        super()
        self.init_type_map()
        self.cache = CacheManager()

    def migrate(self):
        for doctype in app.models:
            meta = app.get_meta(doctype)
            base_doctype = meta.get_base_doctype()
            if not meta.is_single:
                if self.table_exists(base_doctype):
                    self.alter_table(base_doctype)
                else:
                    self.create_table(base_doctype)
        self.commit()

    def create_table(self, doctype, new_name = None):
        table_def = ODict(
            columms = [],
            foreign_keys = [],
            indexes = []
        )
        meta = app.get_meta(doctype)

        for field in meta.get_valid_fields(with_children = False):
            if field.fieldtype in self.type_map:
                self.update_column_definition(field, table_def)
        
        self.run_create_table_query(new_name or doctype, table_def)

    def table_exists(self, table):
        pass

    def run_create_table_query(self, doctype, table_def):
        pass

    def update_column_definition(self, field, table_def):
        pass

    def alter_table(self, doctype):
        diff = self.get_column_diff(doctype)

        new_foreign_keys = self.get_new_foreign_keys(doctype)

        if diff.added:
            self.add_columns(doctype, diff.added)

        if diff.removed:
            self.remove_columns(doctype, diff.removed)

        if new_foreign_keys:
            self.add_foreign_keys(doctype, new_foreign_keys)

    
    def get_column_diff(self, doctype):

        table_columns = self.get_table_columns(doctype)
        valid_fields = app.get_meta(doctype).get_valid_fields(with_children=False)
        valid_field_names = map(lambda df: df.fieldname, valid_fields)
        diff = ODict(added=[], removed=[])

        for field in valid_fields:
            if field.fieldname not in table_columns \
                and field.fieldtype in self.type_map:
                diff.added.append(field)
        
        for column in table_columns:
            if column not in valid_field_names:
                diff.removed.append(column)

        return diff

    def add_columns(self, doctype, added):
        for column in added:
            self.run_add_column_query(doctype, field)

    def remove_columns(self, doctype, removed):
        for column in removed:
            self.run_remove_column_query(doctype, column)

    def get_new_foreign_keys(self, doctype):
        foreign_keys = self.get_foreign_keys(doctype)
        new_foreign_keys = []
        meta = app.get_meta(doctype)

        for field in meta.get_valid_fields(with_children = False):
            # TODO Dynamic Links
            if field.fieldtype == 'Link' \
                and field.fieldname not in foreign_keys:
                new_foreign_keys.append(field)

        return new_foreign_keys
        
    def add_foreign_keys(self, doctype, new_foreign_keys):
        for field in new_foreign_keys:
            self.add_foreign_key(doctype, field)

    def get_foreign_key(self, doctype, field):
        pass

    def get_table_columns(self, doctype):
        pass

    def run_add_column_query(self, doctype, field):
        pass

    def get(self, doctype, name = None, fields = '*'):
        meta = app.get_meta(doctype)

        if meta.is_single:
            doc = self.get_single(doctype)
            doc.name = doctype
        else:
            if not name:
                raise iampy.errors.ValueError('Name is mandatory!')
            doc = self.get_one(doctype, name, fields)
        
        if not doc:
            return

        self.load_children(doc, meta)
        return doc

    def load_children(self, doc, meta):
        table_fields = meta.get_table_fields()
        form_fields = meta.get_form_fields()

        for field in table_fields:
            doc[field.fieldname] = self.get_all(
                doctype = field.childtype,
                fields = ['*'],
                filters = {'parent': doc.name},
                order_by = 'idx',
                order = 'asc'
            )
        
        for field in form_fields:
            doc[field.fieldname] = self.get_one(
                doctype = field.childtype,
                fields = ['*'],
                filters = {'parent': doc.name},
            )
        
    def get_single(self, doctype):
        return ODict(
            row.fieldname: row.value
            for row in self.get_all(
                doctype = 'SingleValue',
                fields = ['fieldname', 'value'],
                filters = {
                    'parent': doctype
                },
                order = 'asc'
            )
        )

    def get_one(self, doctype, name, fields = '*'):
        return self.get(
                doctype = doctype,
                fields = fields,
                filters = {'name': name} if isinstance(name, str) else name,
                limit = 1,
                first = True
            )

    def prepare_fields(self, fields):
        return ", ".join(fields)

    def trigger_change(self, doctype, name):
        self.trigger('change:{}'.format(doctype), name=name)
        self.trigger('change', doctype=docype, name=name)
        meta = app.get_meta(doctype)
        if meta.based_on:
            self.trigger.change(meta.based_on, name)

    def insert(self, doctype, doc):
        meta = app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()

        doc = self.apply_base_doctype_filters(doctype, doc)

        if meta.is_single:
            self.update_single(doctype, doc)
        else:
            self.insert_one(base_doctype, doc)

        # insert children
        self.insert_children(meta, doc, base_doctype)

        self.trigger_change(doctype, doc.name)

        return doc

    def insert_one(self, doctype, doc):
        pass

    def update(self, doctype, doc):
        meta = app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()

        doc = self.apply_base_doctype_filters(doctype, doc)

        # update parent
        if meta.is_single:
            self.update_single(meta, doc, doctype)
        else:
            self.update_one(base_doctype, doc)

        # insert or update children
        self.update_children(meta, doc, base_doctype)

        self.trigger_change(doctype, doc.name)

        return doc

    
    def update_children(self, meta, doc, doctype):
        for field in meta.get_table_fields():
            added = []

            for child in (doc[field.fieldname] or []):
                self.prepare_child(doctype, doc.name, child, field, len(added))
                if self.exists(field.childtype, child.name):
                    self.update_one(field.childtype, child)
                else:
                    self.insert_one(field.childtype, child)
                added.append(child.name)
            
            self.run_delete_other_children(field, doc.name, added)

        for field in meta.get_form_fields():
            child = doc[field.fieldname] or ODict()
            self.prepare_child(doctype, doc.name, child, field, 1)
            if self.exists(field.childtype, child.name):
                self.update_one(field.childtype, child)
            else:
                self.insert_one(field.childtype, child)
            self.run_delete_other_children(field, doc.name, [child.name])

    def update_one(self, doctype, doc):
        pass
        #valid_fields = self.get_valid_fields(doctype)
        #fields_to_update = filter(lambda f: f != 'name', doc.keys())
        #fields = filter(lambda df, u=fields_to_update, field.fieldname in u, valid_fields)
        #formatted_doc = self.get_formatted_doc(fields, doc)

    def run_delete_other_children(self, field, parent, added):
        pass

    def update_single(self, doctype, doc):
        meta = app.get_meta(doctype)
        self.delete_single_values(doctype)

        for field in self.get_valid_fields(with_children = False):
            value = doc[field.fieldname]
            if value is not None:
                single_value = app.new_doc({
                    'docype': 'SingleValue',
                    'parent': doctype,
                    'fieldname': field.fieldname,
                    'value': value
                })
                single_value.db_insert()
    
    def delete_single_values(self, name):
        pass

    def rename(self, docype, old_name, new_name):
        pass

    def prepare_child(self, parenttype, parent, child, field, idx):
        if not child.name:
            child.name = get_random_string()

        child.parent = parent
        child.parenttype = parenttype
        child.parentfield = field.fieldname
        child.idx = idx

    def get_keys(self, doctype):
        return app.get_meta(doctype).get_valid_fields(with_children = False)

    def get_valid_fields(self, doctype):
        return app.get_meta(doctype).get_valid_fields(with_children = False)
    
    def get_formatted_doc(self, fields, doc):
        return {
            field.fieldname: self.get_formatted_value(field, doc.get(field.fieldname))
            for field in fields
        }

    def get_formatted_values(self, fields, doc):
        return [
            self.get_formatted_value(field, doc[field.fieldname])
            for field in fields
        ]

    def get_formatted_value(self, field, value):
        import datetime

        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        elif value is None:
            return None
        return value

    def apply_base_doctype_filters(self, doctype, doc):
        meta = app.get_meta(doctype)
        if meta.filters:
            for field, value in meta.filters.items():
                doc[field] = value

    def delete_many(self, doctype, names):
        for name in names:
            self.delete(doctype, name)

    def delete(self, doctype, name):
        meta = app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()
        self.delete_one(base_doctype, name)

        # delete children
        for field in meta.get_table_fields():
            self.delete_children(field.childtype, name)

        for field in meta.get_form_fields():
            self.delete_children(field.childtype, name)

    def delete_one(self, doctype, name):
        pass

    def delete_children(self, parenttype, parent):
        pass

    def exists(self, doctype, name):
        return bool(self.get_value(doctype, name))

    def get_value(self, doctype, filters, fieldname = 'name'):
        meta = app.get_meta(doctype)
        base_doctype = app.get_base_doctype()
        if isinstance(filters, str):
            filters = {'name': filters}
        if meta.filters:
            filters.update(meta.filters)
        
        row = self.get_all(
            doctype = base_doctype,
            fields = [fieldname],
            filters: filters,
            start = 0,
            limit = 1,
            order_by = 'name',
            order = 'asc'
        )

        return row[0][fieldname] if row else None

    def set_value(self, doctype, name, fieldname, value):
        return self.set_values(doctype, name, {
            fieldname: value
        })

    def set_values(self, doctype, name, values):
        doc = values.copy()
        doc['name'] = name
        return self.update_one(doctype, doc)

    def get_cached_value(self, doctype, name, fieldname):
        value = self.cache.hget('{doctype}:{name}'.format(doctype, name), fieldname)
        if value is None:
            value = self.get_value(doctype, name, fieldname)
        return value

    def get_all(self,
                doctype, 
                fields,
                filters,
                limit = None,
                offset = None,
                group_by = None,
                order_by = 'creation',
                order = 'desc'):
        
        meta = app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()

        if not fields:
            fields = meta.get_keyword_fields()
            fields.insert(0, 'name')
        elif isinstance(fields, str):
            fields = [fields]

        if meta.filters:
            filters.update(meta.filters)

        sql = 'SELECT {fields} FROM {base_doctype} '
        sql, args = self.get_filter_conditions(filters)

        if order_by:
            sql += ' ORDER BY {order_by} {order}'
        
        if group_by:
            sql += ' GROUP BY {group_by}'

        if limit:
            sql += ' LIMIT {limit}'
            if offset:
                sql += ' OFFSET {offset}'
        
        return self.sql(sql.format(**locals()), args)

    def get_filter_conditions(self, filters):
        # {"status": "Open"} => `status = "Open"`
        #
        # {"status": "Open", "name": ["like": "apple%"]} => `status = "Open" and name like "apple%"`
        #
        # {"date": [">=", "2017-09-09", "<=", "2017-11-01"]} => `date >= "2017-09-09" and date <= "2017-11-01"`
        #
        # {"date": ["between", ["2017-09-09", "2017-11-01"]} => `date between "2017-09-09" and date <= "2017-11-01"`

        args, where_list = [], []
        where = lambda args: " ".join(args)

        for field, value in filters.items(): 
            operator = '='
            comparison_value = value

            if isinstance(value, list):
                while value :
                    if len(value) > 2:
                        operator, comparison_value = value.pop(0), value.pop(1)
                        placeholder = "?"
                        operator = operator.lower()

                        if isinstance(comparison_value, list):
                            if operator == "between":
                                placeholder = '? and ?'
                            else: # in operator
                                placeholder = '({})'.format(','.join("?" * len(value)))
                        
                        if operator == 'like' and '%' not in comparison_value:
                            comparison_value = "%{}%".format(comparison_value)

                        where_list.append(where([field, operator, placeholder]))
                        if not isinstance(comparison_value, list):
                            args.append(comparison_value)
                        else:
                            args.extend(comparison_value)
                    else:
                        where_list.append(where([field, "=", "?"]))
                        args.append(value.pop(0))

            else:
                where_list.append(where([field, operator, "?"]))
                args.append(value)

        if where_list:
            return " WHERE {}".format(" AND ".join(where_list)), args
        return "", []

    def run(self, query, params = ()):
        return self.sql(query, params)

    def sql(self, query, params = ()):
        pass

    def commit(self):
        try:
            self.sql('commit')
        except iampy.errors.CannotCommitError as e:
            pass
        except Exception as e:
            raise e
    
    def clear_value_cache(self, doctype, name):
        key = ":".join([doctype, name])
        self.cache.hclear(key)

    def get_column_type(self, field):
        return self.type_map[field.fieldtype]

    def get_error(self, e):
        return iampy.errors.DatabaseError(e)

    def init_type_map(self):
        return self.type_map = ODict()