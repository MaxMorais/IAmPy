from iampy.utils.observable import ODict
from iampy.utils import slug

DocField = ODict(
    name = "DocField",
    label="Fields",
    doctype="DocType",
    description='Master table of all table fields, the maintenance of this information is made from `DocType` form',
    is_single=0,
    is_tree=0,
    is_child=1,
    is_submittable=0,
    keyword_fields=[
        "name",
        "label",
        "fieldtype",
        "fieldname",
        "required",
        "options"
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
            fieldname="childtype",
            label="Child Type",
            fieldtype="Link",
            target="DocType"
        ),
        ODict(
            fieldname='precision',
            label='Precision',
            fieldtype='Int'
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