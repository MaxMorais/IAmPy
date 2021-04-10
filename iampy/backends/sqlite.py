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


    def add_foreign_keys(self, doctype, new_foreign_keys):
        self.run('PRAGMA foreign_keys=OFF')
        self.run('BEGIN TRANSACTION')

        temp_name = 'TEMP_{}'.format(doctype)

        self.create_table(doctype, temp_name)

        columns = ", ".join(self.get_table_columns(temp_name))

        # copy from old to new table
        self.run('INSERT INTO {temp_name} ({columns}) SELECT {column} FROM {doctype}'.format(
            **locals()
        ))

        # drop old table
        self.run('DROP TABLE {doctype}'.format(**locals()))

        # rename new table
        self.run('ALTER TABLE {temp_name} RENAME TO {doctype}'.format(**locals()))

        self.commit()
        self.run('PRAGMA foreign_keys=ON')

    def remove_columns(self):
        # TODO: need new version of sqlite
        pass

    def run_create_table_query(self, doctype, table_def):

        columns = ", ".join(table_def.columns)
        foreign_keys = ", {}".format(", ".join(table_def.foreign_keys)) if table_def.foreign_keys else ''
        query = 'CREATE TABLE IF NOT EXISTS {doctype} ({columns}{foreign_keys});'.format(
            doctype=doctype,
            columns=columns,
            foreign_keys=foreign_keys
        )

        self.run(query)

        for index in (table_def.indexes or []):
            query = "CREATE {unique}INDEX idx_{doctype}_{field} ON {doctype}({field});".format(
                doctype=doctype,
                field = index.field,
                unique = 'UNIQUE ' if index.unique else ''
            )
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
            default_value = "'{}'".format(default_value)
        
        return " ".join([
            field.fieldname,
            self.type_map[field.fieldtype],
            'PRIMARY KEY NOT NULL' if field.fieldname == 'name' else '',
            'NOT NULL' if field.required else '',
            'DEFAULT {}'.format(default_value) if field.default else ''
        ]).strip()

    def get_foreign_key_definition(self, doctype, field):
        return "FOREIGN KEY ({fieldname}) REFERENCES {doctype}(name) ON UPDATE CASCADE ON DELETE RESTRICT".format(
            doctype=doctype,
            fieldname=field.fieldname
        )

    def get_table_columns(self, doctype):
        return map(lambda d: d.name, self.sql('PRAGMA table_info({})'.format(doctype)))
    
    def get_foreign_keys(self, doctype):
        return map(lambda d: d['from'], self.sql('PRAGMA foreign_key_list({})'.format(doctype)))

    def run_add_column_query(self, doctype, field, values):
        self.run('ALTER TABLE {doctype} ADD COLUMN {col_def}'.format(
            doctype = doctype,
            col_def = self.get_column_definition(col_def)
        ), values)

    def insert_one(self, doctype, doc):
        fields = self.get_keys(doc)
        placeholders = ','.join(['?'] * len(fields))
        colums = ','.join(map(lambda f: f.fieldname, fields))
        if not doc.name:
            doc.name = get_random_string()
        
        return self.run(" ".join([
            "INSERT INTO {doctype} ({fields}) VALUES ({placeholders})".format(**locals()),
            self.get_formatted_values(fields, doc)
        ]))

    def update_one(self, docype, doc):
        fields = self.get_keys(doctype)
        assigns = map(lambda f: '{} = ?'.format(f.fieldname))
        values = self.get_formatted_values(fields, doc)

        # additional name for where clause
        values.append(doc.name)

        return self.run('UPDATE {doctype} SET {assigns} WHERE name = ?'.format(
            **locals()
        ),  values)

    def run_delete_other_children(self, field, parent, added):
        # delete other children
        added.append(parent)
        return self.run('DELETE FROM {doctype} WHERE parent ? AND name nam no in ({added})'.format(
            doctype = field.childtype,
            added = ' '.join(['?'] * len(added) - 1)
        ), added)

    def delete_one(self, doctype, name):
        return self.run('DELETE FROM {doctype} WHERE name = ?'.format(
            doctype=doctype
        ), [name])

    def delete_children(self, doctype, parent):
        return self.run('DELETE FROM {doctype} WHERE parent = ?'.format(
            doctype = doctype,
            parent = parent
        ))

    def delete_single_values(self, name):
        return self.run('DELETE FROM SingleValue WHERE parent=?', [name])

    def rename(self, doctype, old_name, new_name):
        meta = self.app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()
        self.run('UPDATE ${base_doctype} SET name = ? WHERE name = ?'.format(
            base_doctype = base_doctype,
        ), [new_name, old_name])
        self.commit()

    def set_values(self, doctype, name, field_value_pair):
        meta = self.app.get_meta(doctype)
        base_doctype = meta.get_base_doctype()
        valid_fields = self.get_keys(doctype)
        valid_fieldnames = map(lambda df: df.fieldname, valid_fields)
        fields_to_update = list(filter(lambda df, vf=valid_fieldnames: df.fieldname in vf, field_value_pair.keys()))

        # assignment part of query
        assigns = ", ".join(map(lambda df: '{df.fieldname} = ?'.format(df = df)))

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

        return self.run('UPDATE {base_doctype} SET {assigns} WHERE name = ?'.format(
            base_doctype = base_doctype,
            assigns = assigns
        ), values)

    def sql(self, query, params=()):
        return self.conn.execute(query, params)

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
    
    
    