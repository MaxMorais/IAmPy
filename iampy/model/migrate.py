
import iampy.errors
from iampy import app
from iampy.utils.observable import ODict

def migrate(all_patches, patch_order):
    executed_patch_runs = []

    try:
        executed_patch_runs = map(lambda d: d.name, iampy.db.get_all('PatchRun', fields=['name']))
    except iampy.errors.DatabaseError as e:
        pass

    def mapper(text):
        patch = text.split(' ')
        if text and patch:
            return Odict(
                filename: text,
                method: all_patches[patch]
            )
    
    patch_run_order = filter(None, map(mapper, patch_order))

    for patch in patch_run_order:
        if not patch.filename in executed_patch_runs:
            run_patch(patch)


def run_patch(patch):
    try:
        patch.method()
        patch_run = app.get_new_doc('PatchRun')
        patch_run.name = patch.filename
        patch_run.save()
    except Exception as error:
        print(str(error))
        print(f'Could not run patch {patch}')
