from iampy.utils.observable import ODict
from iampy.utils import slug

DocField = ODict(
    name = "DocField",
    label="Fields",
    doctype="DocType",
    is_single=0,
    is_tree=0,
    is_child=1,
    keyword_fields=[
        "name",
        "label",
        "is_single",
        "is_tree",
        "is_child"
    ],
    fields=[
        ODict(
            fieldname="label",
            label="Label",
            fieldtype="Data",
            required = 1
        ),
        ODict(
            fieldname="fieldtype",
            label="Type",
            fieldtype="Link",
            required=1,
            target="FieldType",
            default="Data"
        ),
        ODict(
            fieldname="fieldname",
            label="Name",
            fieldtype="Data",
            required=1,
            formula=lambda doc: slug(doc.label).replace('-', '_')
        ),
        ODict(
            fieldname="required",
            label="Required?",
            fieldtype="Check",
            default=0
        ),
        ODict(
            fieldname="options",
            label="Options",
            fieldtype="Small Text"
        ),
        ODict(
            fieldname="target",
            label="Target",
            fieldtype="Link",
            target="DocType"
        ),
        ODict(
            fieldname="child_type",
            label="Child Type",
            fieldtype="Link",
            target="DocType"
        ),
        ODict(
            fieldname="formula",
            label="Formula",
            fieldtype="Code"
        ),
        ODict(
            fieldname="validator",
            label="Validator",
            fieldtype="Code"
        )
    ]
)