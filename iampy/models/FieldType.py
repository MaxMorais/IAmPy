from iampy.utils.observable import ODict

FieldType = ODict(
    name="FieldType",
    label="Field Type",
    doctype="DocType",
    description='Master table of all FieldTypes into the System, users can define they own custom fields types.',
    is_single=0,
    is_tree=0,
    is_child=0,
    is_submittable=0,
    keyword_fields=[
        'name',
        'virtual'
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
            options='Python',
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