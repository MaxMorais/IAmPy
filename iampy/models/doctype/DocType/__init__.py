from iampy.utils.observable import ODict


DocType = ODict(
    name = 'DocType',
    label = 'DocType',
    doctype = 'DocType',
    is_single = 0,
    is_tree = 0,
    is_child = 0,
    keyword_fields = [
        'name', 
        'label', 
        'is_single', 
        'is_tree', 
        'is_child'
    ],
    fields = [
        ODict(
            name = 'name',
            label = 'Name',
            fieldtype = 'Data',
            required = 1
        ),
        ODict(
            name = 'label',
            label = 'Label',
            fieldtype = 'Data',
            required = 1
        ),
        ODict(
            name = 'is_single',
            label = 'Is Single',
            fieldtype = 'Check',
            default = 0
        ),
        ODict(
            name = 'is_tree',
            label = 'Is Tree',
            fieldtype = 'Check',
            default = 0
        ),
        ODict(
            name = 'is_child',
            label = 'Is Child',
            fieldtype = 'Check',
            default = 0
        ),
        ODict(
            name = 'based_on',
            label = 'Based On',
            fieldtype = 'Link',
            target = 'DocType'
        )
        ODict(
            name = 'keyword_fields',
            label = 'Keywords',
            fieldtype = 'Tags',
            default = '[]'
        ),
        ODict(
            name = 'fields',
            label = 'Fields',
            fieldtype = 'Table',
            required = 1,
            childtype = 'DocField'
        )
    ]
)