#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read chosen colours from config file and prepend to style.css
"""
from pathlib import Path
import re
import configparser

def _get_config(static_path):
    config = configparser.ConfigParser()
    config.read(static_path.joinpath('colour.ini'))
    return config

def _read_scheme(name, static_path):
    config = _get_config(static_path)
    colours = config[name]
    return colours
    
def get_color_schemes(static_path):
    config = _get_config(static_path)
    keys = list(config.keys())
    keys.remove('DEFAULT')
    return keys

def _make_css(dct):
    lines = [f"  --{key}: {value};" for key, value in dct.items()]
    lines.insert(0, ":root {")
    lines.append("}")
    css = "\n".join(lines)
    return css

def _write_css(css, static_path):
    for css_file in static_path.glob("css/*.css"):
    # css_file = static_path.joinpath('css', 'style.css')
        with open(css_file) as fileobj:
            text = fileobj.read()
    
        # if there already is a :root element in text, replace it
        # otherwise, add it at beginning       
        regex = re.compile(r":root *\{(?P<content>.*?)\}", re.DOTALL)
        if regex.search(text) is not None:
            text = regex.sub(css, text)
        else:
            text = css + "\n" + text
        
        with open(css_file, 'w') as fileobj:
            fileobj.write(text)
        
def _write_svg(fill_colour, static_path):
    image_path = static_path.joinpath("img")
    for p in image_path.glob("search*.svg"):
        with open(p) as fileobj:
            text = fileobj.read()
        text = re.sub(r'fill="#\w+"', f'fill="{fill_colour}"', text)
        with open(p, 'w') as fileobj:
            fileobj.write(text)
        
def main(scheme_name, static_path):
    colours = _read_scheme(scheme_name, static_path)
    css = _make_css(colours)
    _write_css(css, static_path)
    _write_svg(colours['background-2'], static_path)
    
if __name__ == '__main__':
    
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    
    parser.add_argument('path', help='Path to static dir')
    parser.add_argument('-n', '--name', help='Scheme name')
    parser.add_argument('-l', '--list', help='List available colour scheme',
                        action='store_true')

    args = parser.parse_args()
    
    p = Path(args.path)
    
    if args.list:
        lst = get_color_schemes(p)
        print("Schemes:")
        for name in lst:
            print(f"  {name}")
        
    if args.name is not None:
        main(args.name, p)