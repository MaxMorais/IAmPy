from iampy.utils.observable import ODict

FieldType = ODict(
    name="FieldType",
    label="Field Type",
    doctype="DocType",
    is_single=0,
    is_tree=0,
    is_child=0,
    keyworld_fields=[
        'name',
        'label',
        'is_single',
        'is_tree',
        'is_child'
    ],
    fields=[
        ODict(
            fieldname="fieldtype",
            label="Field Type",
            fieldtype="Data",
            required=1
        ),
        ODict(
            fieldname="virtual",
            label="Is Virtual?",
            fieldtype="Check",
            default=0
        ),
        ODict(
            fieldname="sql",
            label="SQL",
            fieldtype="Code",
            description="Contains the SQL fieldtype eg: `INT NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT`"
        ),
        ODict(
            fieldname="python",
            label="Python",
            fieldtype="Code",
            description="Contains the Python code to handle the fieldtype eg: `int(value or 0)`"
        ),
        ODict(
            fieldname="widget",
            label="Widget",
            fieldtype="Code",
            description="Contains the UI code to contruct, handle and validate the widget on the UI"
        )
    ]
)