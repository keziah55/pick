#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add aliases to Person entries in DB.
"""

import warnings
if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys, os
    from pathlib import Path
    sys.path.append(str(Path(__file__).parents[1]))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pick.settings')
    import django
    django.setup()

from mediabrowser.models import Person

def read_csv(patch_csv):
    """ Read values from (tab separated) csv file and apply aliases to names """
    with open(patch_csv) as fileobj:
        text = fileobj.read()
        
    header, *lines = [line for line in text.split("\n") if line]
    
    for line in lines:
        name, alias = [s.strip() for s in line.split("\t")]
        add_alias(name, alias)
    
def add_alias(name, alias):
    """ Find Person with `name` and set their alias to `alias` """
    persons = Person.objects.filter(name=name)
    if len(persons) == 0:
        warnings.warn(f"Person '{name}' not found", UserWarning)
        return
    person = persons[0]
    person.alias = alias
    person.save()
    return person

if __name__ == "__main__":
    
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    
    parser.add_argument('-p', '--patch', help='Path to patch csv')

    args = parser.parse_args()
    
    read_csv(args.patch)