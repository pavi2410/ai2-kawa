#!/usr/bin/env python3
"""Lists the Kawa classes an App Inventor app can never load on the device.

    python3 appinventor-runtime-classes.py kawa-1.11-compiler.jar > classes-to-skip-for-appinventor-runtime

App Inventor needs the full Kawa jar to compile YAIL (kawa.repl -C), but on the
device an app only needs the Scheme runtime and evaluator. This script starts
from the classes App Inventor's runtime enters Kawa through (kawa.standard.Scheme,
gnu.expr.Language and kawa.Shell) and follows two kinds of references between
classes:

  * direct references: class constants and class names in field and method
    descriptors, which the JVM or ART resolve when the code runs;
  * class names written as strings (for example "kawa.lib.lists" in Scheme's
    table of built-ins), which Kawa passes to Class.forName.

String references into SKIP are not followed: they are only loaded for other
languages (XQuery, XSLT, ECMAScript, Common Lisp), the servlet and SAX glue, the
desktop GUI and REPL, or by (require 'srfi-N), which YAIL never emits. Direct
references are always followed, so a class stays if anything reachable refers to
it directly.

Every class that is not reached is printed as a jar path. The ant target
appinventor-runtime-jar leaves those classes out of kawa-<version>-runtime.jar.
Regenerate the list whenever Kawa's sources change.
"""
import re
import struct
import sys
import zipfile

ROOTS = ('kawa.standard.Scheme', 'gnu.expr.Language', 'kawa.Shell')

SKIP = re.compile(
    r'^gnu\.(xquery|commonlisp|ecmascript|jemacs|brl|kawa\.(xslt|swingviews|models|servlet|sax))\.'
    r'|^kawa\.(GuiConsole|GuiInPort|PaintableView|Repl|TextPaneWriter|Telnet|repl$)'
    r'|^gnu\.kawa\.slib\.(?!cut|enums|DefineRecordType)')

DESCRIPTOR_CLASS = re.compile(r'L([A-Za-z0-9_$/]+);')


def references(data):
    """Returns (direct, strings) for a class file: the class names it refers to
    directly, and all of its UTF-8 constants."""
    count = struct.unpack('>H', data[8:10])[0]
    i, k = 10, 1
    utf8, class_entries = {}, []
    while k < count:
        tag = data[i]
        if tag == 1:  # Utf8
            length = struct.unpack('>H', data[i + 1:i + 3])[0]
            utf8[k] = data[i + 3:i + 3 + length].decode('utf-8', 'replace')
            i += 3 + length
        elif tag == 7:  # Class
            class_entries.append(struct.unpack('>H', data[i + 1:i + 3])[0])
            i += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            i += 5
        elif tag in (5, 6):  # Long and Double take two slots
            i += 9
            k += 1
        elif tag in (8, 16, 19, 20):
            i += 3
        elif tag == 15:
            i += 4
        else:
            raise ValueError('unknown constant pool tag %d' % tag)
        k += 1
    direct = set()
    for index in class_entries:
        name = utf8[index].lstrip('[')
        if name.startswith('L') and name.endswith(';'):
            name = name[1:-1]
        direct.add(name.replace('/', '.'))
    for value in utf8.values():
        for match in DESCRIPTOR_CLASS.finditer(value):
            direct.add(match.group(1).replace('/', '.'))
    return direct, set(utf8.values())


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with zipfile.ZipFile(sys.argv[1]) as jar:
        classes = {name[:-6].replace('/', '.'): references(jar.read(name))
                   for name in jar.namelist() if name.endswith('.class')}

    def named_in(strings):
        found = set()
        for s in strings:
            for candidate in (s, s.split('$')[0]):
                if candidate in classes and not SKIP.search(candidate):
                    found.add(candidate)
        return found

    reached, todo = set(), list(ROOTS)
    while todo:
        name = todo.pop()
        if name in reached:
            continue
        reached.add(name)
        direct, strings = classes[name]
        todo.extend(({d for d in direct if d in classes} | named_in(strings)) - reached)

    for name in sorted(set(classes) - reached):
        print(name.replace('.', '/') + '.class')


if __name__ == '__main__':
    main()
