
import re
from iampy import errors

def email(value):
    if not re.match('(.+)@(.+){2,}', value):
        raise errors.ValidationError(f'Invalid Email: {value}')

def phone(value):
    if not re.match(f'[+]{0,1}[\d]', value):
        raise errors.ValidationError(f'Invalid Phone: {value}')