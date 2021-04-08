
import re
import iampy.errors

def email(value):
    if not re.match('(.+)@(.+){2,}', value):
        raise iampy.errors.ValidationError(f'Invalid Email: {value}')

def phone(value):
    if not re.match(f'[+]{0,1}[\d]', value):
        raise iampy.errors.ValidationError(f'Invalid Phone: {value}')