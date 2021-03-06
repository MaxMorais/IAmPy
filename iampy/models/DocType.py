from iampy.utils.observable import ODict


DocType = ODict(
    name = 'DocType',
    label = 'DocType',
    doctype = 'DocType',
    description = 'Master table of all Meta-Data, containing the description of all tables, and allowing users to define new tables.',
    is_single = 0,
    is_tree = 0,
    is_child = 0,
    is_submittable = 0,
    keyword_fields = [
        'label', 
        'description',
        'is_single', 
        'is_tree', 
        'is_child',
        'is_submittable'
    ],
    fields = [
        ODict(
            fieldname = 'name',
            label = 'Name',
            fieldtype = 'Data',
            required = 1
        ),
        ODict(
            fieldname = 'label',
            label = 'Label',
            fieldtype = 'Data',
            required = 1
        ),
        ODict(
            fieldname = 'description',
            label = 'Description',
            fieldtype = 'Small Text'
        ),
        ODict(
            fieldname = 'is_single',
            label = 'Is Single?',
            fieldtype = 'Check',
            default = 0
        ),
        ODict(
            fieldname = 'is_tree',
            label = 'Is Tree?',
            fieldtype = 'Check',
            default = 0
        ),
        ODict(
            fieldname = 'is_child',
            label = 'Is Child?',
            fieldtype = 'Check',
            default = 0
        ),
        ODict(
            fieldname='is_submittable',
            label='Is Submittable?',
            fieldtype='Check',
            default = 0
        ),
        ODict(
            fieldname = 'based_on',
            label = 'Based On',
            fieldtype = 'Link',
            target = 'DocType'
        ),
        ODict(
            fieldname = 'keyword_fields',
            label = 'Keywords',
            fieldtype = 'Tags',
            default = []
        ),
        ODict(
            fieldname = 'fields',
            label = 'Fields',
            fieldtype = 'Table',
            required = 1,
            childtype = 'DocField'
        ),
        ODict(
            fieldname='hidden',
            label='Hidden?',
            fieldtype='Check',
            default=0
        )
    ]
)