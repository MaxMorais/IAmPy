import sqlite3
from collections import namedtuple
from .database import Database, ODict, get_random_string

def Row(cursor, row):
    return ODict(list(zip(
        [col[0] for col in cursor.description],
        row
    )))
    
class SQLiteDatabase(Database):

    def connect(self):
        dictrows = self.app.config.db.dictrows 
        text_factory = self.app.config.db.text_factory or str
        functions = self.app.config.db.functions or {}
        aggregates = self.app.config.db.aggregates or {}
        collations = self.app.config.db.collations or {}
        extensions = self.app.config.db.extensions or ()

        self.conn = sqlite3.connect(self.app.config.db.file, **self.app.config.db.connection_params)
        self.conn.text_factory = text_factory

        if dictrows:
            self.conn.row_factory = Row

        for name, value in functions.items():
            self.conn.create_function(name, *value)
        for name, value in aggregates.items():
            self.conn.create_aggregate(name, *value)
        for name in collations.items():
            self.conn.create_collation(name, value)
        for name in extensions:
            self.conn.enable_load_extension(True)
            self.conn.execute('SELECT load_extension(?)', (name,))
            self.conn.enable_load_extension(False)
        
        self.run('PRAGMA foreign_keys=ON')

        if self.app.config.db.debug:
            self.conn.set_trace_callback(print)

    def table_exists(self, table):
        res = self.sql('SELECT count(name) as [exists] FROM sqlite_master WHERE name=? AND type=?', (
            table, 'table'
        )).fetchone()
        return bool(res[0])

    def disable_foreign_keys(self):
        self.run('PRAGMA foreign_keys=OFF')

    def enable_foreign_keys(self):
        self.run('PRAGMA foreign_keys=ON')

    def add_foreign_keys(self, doctype, new_foreign_keys):
        self.disable_foreign_keys()
        self.run('BEGIN TRANSACTION')

        temp_name = f'TEMP_{doctype}'

        self.create_table(doctype, temp_name)

        columns = ", ".join(self.get_table_columns(temp_name))

        # copy from old to new table
        self.run(f'INSERT INTO {temp_name} ({columns}) SELECT {column} FROM {doctype}')

        # drop old table
        self.run(f'DROP TABLE {doctype}')

        # rename new table
        self.run(f'ALTER TABLE {temp_name} RENAME TO {doctype}')

        self.commit()
        self.enable_foreign_keys()

    def remove_columns(self):
        # TODO: need new version of sqlite
        pass

    def run_create_table_query(self, doctype, table_def):

        columns = ", ".join(table_def.columns)
        foreign_keys = ", {}".format(", ".join(table_def.foreign_keys)) if table_def.foreign_keys else ''
        query = f'CREATE TABLE IF NOT EXISTS {doctype} ({columns}{foreign_keys});'

        self.run(query)

        for index in (table_def.indexes or []):
            unique = 'UNIQUE ' if index.unique else ''
            query = f"CREATE {unique}INDEX idx_{doctype}_{field} ON {doctype}({field});"
            self.run(query)

    def update_column_definition(self, field, table_def):
        table_def.columns.append(self.get_column_definition(field))

        # TODO Dynamic Links
        if field.fieldtype == 'Link' and field.target:
            meta = self.app.get_meta(field.target)
            table_def.foreign_keys.append(
                self.get_foreign_key_definition(meta.get_base_doctype(), field)
            )
        
        if field.indexed or field.unique:
            table_def.indexes.append(ODict(
                unique = field.unique,
                field = field.fieldname
            ))

    def get_column_definition(self, field):
        default_value = field.default

        # TODO: need support to SQLite3 functions
        if isinstance(default_value, str):
            default_value = f"'{default_value}'"
        
        return " ".join([
            field.fieldname,
            self.type_map[field.fieldtype],
            'PRIMARY KEY NOT NULL' if field.fieldname == 'name' else '',
            'NOT NULL' if field.required else '',
            f'DEFAULT {default_value}' if field.default else ''
        ]).strip()

    def get_foreign_key_definition(self, doctype, field):
        return f"FOREIGN KEY ({field.fieldname}) REFERENCES {doctype}(name) ON UPDATE CASCADE ON DELETE RESTRICT"

    def get_table_columns(self, doctype):
        return list(map(lambda d: d.name, self.sql(f'PRAGMA table_info({doctype})')))
    
    def get_foreign_keys(self, doctype):
        return list(map(lambda d: d['from'], self.sql(f'PRAGMA foreign_key_list({doctype})')))

    def run_add_column_query(self, doctype, field, values):
        col_def = self.get_column_definition(field)
        self.run(f'ALTER TABLE {doctype} ADD COLUMN {col_def}', values)

    def get_one(self, doctype, name, fields='*'):
        meta = self.app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()
        fields = self.prepare_fields(fields)

        sql = f'SELECT {fields} FROM {base_doctype} WHERE name = ?'
        return self.sql(sql, (name, )).fetchone()


    def insert_one(self, doctype, doc):
        fields = self.get_keys(doctype)
        placeholders = ','.join(['?'] * len(fields))
        columns = ','.join([df.fieldname for df in fields])

        if not doc.name:
            doc.name = get_random_string()

        return self.run(
            f"INSERT INTO {doctype} ({columns}) VALUES ({placeholders})",
            self.get_formatted_values(fields, doc)
        )

    def update_one(self, doctype, doc):
        fields = self.get_keys(doctype)
        assigns = ", ".join(map(lambda f: f'{f.fieldname} = ?'))
        values = self.get_formatted_values(fields, doc)

        # additional name for where clause
        values.append(doc.name)

        return self.run(f'UPDATE {doctype} SET {assigns} WHERE name = ?',  values)

    def run_delete_other_children(self, field, parent, added):
        # delete other children
        added.append(parent)
        placeholders = ' '.join(['?'] * len(added) - 1)
        return self.run(f'DELETE FROM {field.childtype} WHERE parent ? AND name NOT IN ({placeholders})', added)

    def delete_one(self, doctype, name):
        return self.run(f'DELETE FROM {doctype} WHERE name = ?', [name])

    def delete_children(self, doctype, parent):
        return self.run(f'DELETE FROM {doctype} WHERE parent = ?', (parent,))

    def delete_single_values(self, name):
        return self.run('DELETE FROM SingleValue WHERE parent=?', [name])

    def rename(self, doctype, old_name, new_name):
        meta = self.app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()
        self.run(f'UPDATE {base_doctype} SET name = ? WHERE name = ?', (new_name, old_name))
        self.commit()

    def set_values(self, doctype, name, field_value_pair):
        meta = self.app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()
        valid_fields = self.get_keys(doctype)
        valid_fieldnames = tuple(map(lambda df: df.fieldname, valid_fields))
        fields_to_update = list(filter(lambda df, vf=valid_fieldnames: df.fieldname in vf, field_value_pair.keys()))

        # assignment part of query
        assigns = ", ".join(map(lambda df: f'{df.fieldname} = ?'))

        # values
        values = [
            self.get_formatted_value(
                self.get_formatted_value(
                    meta.get_field(fieldname),
                    field_value_pair[fieldname]
                )
            )
            for fieldname in fields_to_update
        ]

        # additional name for where clause
        values.append(name)

        return self.run(f'UPDATE {base_doctype} SET {assigns} WHERE name = ?', values)

    def sql(self, query, params=()):
        try:
            return self.conn.execute(query, params)
        except sqlite3.InterfaceError:
            import pdb; pdb.set_trace()

    def init_type_map(self):

        T, I, R = 'TEXT', 'INTEGER', 'REAL'

        self.type_map = ODict({
            'Currency': R,
            'Float': R,
            'Percent': R,
            'Check': I,
            'Int': I,
            'AutoComplete': T,
            'Small Text': T,
            'Long Text': T,
            'Code': T,
            'Text Editor': T,
            'Date': T,
            'Datetime': T,
            'Time': T,
            'Text': T,
            'Data': T,
            'Link': T,
            'Dynamic Link': T,
            'Password': T,
            'Select': T,
            'Read Only': T,
            'File': T,
            'Attach': T,
            'Attach Image': T,
            'Signature': T,
            'Color': T,
            'Barcode': T,
            'Geolocation': T,
            'Tags': T
        })

        self.virtual_types = (
            'Section Break',
            'Column Break',
            'HTML',
            'Table',
            'Table MultiSelect',
            'Button',
            'Image',
            'Fold',
            'Heading'
        )
    
    
    