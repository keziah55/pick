#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Small script to force update from patch csv (unlike PopulateDatabase.update that
only updates when IMDb ID doesn't match).

You can specify start and stop row numbers, to only update from those rows.
"""

if __name__ == "__main__":
    # https://docs.djangoproject.com/en/4.2/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
    import sys, os
    from pathlib import Path
    sys.path.append(Path(__file__).parents[1])
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pick.settings')
    import django
    django.setup()

from populate_db import PopulateDatabase
from mediabrowser.models import VisionItem

def apply_patches(patch_csv, idx0=None, idx1=None):
    patch = PopulateDatabase._read_patch_csv(patch_csv)
    
    if idx0 is not None and idx1 is not None:
        keys = list(patch.keys())[idx0:idx1]
    elif idx0 is not None and idx1 is None:
        keys = list(patch.keys())[idx0:]
    elif idx0 is None and idx1 is not None:
        keys = list(patch.keys())[:idx1]
    else:
        keys = list(patch.keys())
        
    for file in keys:
        dct = patch[file]
        item = VisionItem.objects.get(filename=file)
        
        for key, value in dct.items():
            setattr(item, key, value)
        item.save()
            
        print(f"Updated {item.title}, {item.imdb_id}")
        
if __name__ == "__main__":
    
    import argparse   
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-p', '--patch', help='Path to patch csv')
    parser.add_argument('-i0', '--idx0', help='Index to start from', type=int)
    parser.add_argument('-i1', '--idx1', help='Index to stop at', type=int)

    args = parser.parse_args()
    apply_patches(args.patch, args.idx0, args.idx1)