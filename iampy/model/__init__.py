
from copy import deepcopy
from iampy.utils.observable import ODict

def extend(base, target, **options):
    base = deepcopy(base)
    fields_to_merge = map(lambda df: df.fieldname, target.fields or [])
    fields_to_remove = options.get('skip_fields', [])
    override_props = options.get('override_props', [])

    for prop in override_props:
        if prop in base:
            base.pop(prop)

    fields_added = fields.map(lambda df: df.fieldname)
    fields_to_add = list(filter(lambda df: df.fieldname in fields_added))

    def merge_fields(base_fields, target_fields):
        
        def mapper(df):
            if df.fieldname in fields_to_merge:
                copy = deepcopy(df)
                copy.update(
                    **next(filter(lambda tdf, df=df: tdf.fieldname == df.fieldname, target_fields))
                )
                return copy
        

        fields = deepcopy(base_fields)
        fields = map(mapper, filter(lambda df: df.fieldname not in fields_added))

    fields = merge_fields(base.fields, target.fields or [])
    base.update(target)
    base.fields = list(fields)
    return base


common_fields = [
    ODict(
        fieldname = 'name',
        fieldtype = 'Data',
        required = 1
    )
]

submittable_fields = [
    ODict(
        fieldname = 'submitted',
        fieldtype = 'Check',
        required = 1
    )
]

parent_fields = [
    ODict(
        fieldname = 'owner',
        fieldtype = 'Data',
        required = 1
    ),
    ODict(
        fieldname = 'modified_by',
        fieldtype = 'Data',
        required = 1
    ),
    ODict(
        fieldname = 'creation',
        fieldtype = 'Datetime',
        required = 1
    ),
    ODict(
        fieldname = 'modified',
        fieldtype = 'Datetime',
        required = 1
    ),
    ODict(
        fieldname = 'keywords',
        fieldtype = 'Text'
    )
]

child_fields = [
    ODict(
        fieldname = 'idx',
        fieldtype = 'Int',
        required = 1
    ),
    ODict(
        fieldname = 'parent',
        fieldtype = 'Data',
        required = 1
    ),
    ODict(
        fieldname = 'parenttype',
        fieldtype = 'Data',
        required = 1
    ),
    ODict(
        fieldname = 'parentfield',
        fieldtype = 'Data',
        required = 1
    )
]

tree_fields = [
    ODict(
        fieldname = 'lft',
        fieldtype = 'Int'
    ),
    ODict(
        fieldname = 'rgt',
        fieldtype = 'Int'
    )
]