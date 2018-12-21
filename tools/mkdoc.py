#!/usr/bin/env python
##
## Name:    mkdoc.py
## Purpose: Extract documentation from header files.
##
## Copyright (C) 2018 Michael J. Fromberger. All Rights Reserved.
##
## Usage: mkdoc.py <template> <output>
##
from __future__ import print_function

import collections, re, sys

# A regular expression to match commented declarations.
# This is specific to C and not very general; it should work fine for the imath
# headers but will not adapt well to arbitrary code or to C++.
doc = re.compile(r'''(?mx)/\*\* # open  /**
(?P<text>(?:[^*]|\*[^/])*)      # text      Does a thing
\*/\n                           # close */
(?P<decl>[^;{]*(?:;$|\{))''')  # decl  void f(x);

# A regular expression matching up to 4 spaces at the head of a line.
spc = re.compile(r'(?m)^ {1,4}')

# A regular expression matching an insertion point.  An insertion point has the
# form {{include "header" name ...}}.  If no names are given, all the names in
# the given header are inserted.
ins = re.compile(r'{{insert "(?P<file>[^"]*)"(?P<names>(?:\s+\w+)+)?\s*}}')

# A regular expression matching non-identifier characters, for splitting.
nid = re.compile(r'\W+')

# A cache of already-parsed files, maps filename to declarations.
CACHE = {}


def last_word(s):
    """Returns the last identifier-shaped word in s."""
    return nid.split(s.strip())[-1]


def typeset(text):
    """Renders text with verbatim sections into markdown."""
    lines = []
    fence = False
    for line in text.split('\n'):
        if fence != line.startswith(' '):
            lines.append('```')
            fence = not fence
        lines.append(line)
    if fence:
        lines.append('```')
    for i, line in enumerate(lines):
        if i == 0: lines[i] = ' -  ' + line
        elif line: lines[i] = '    ' + line
    return '\n'.join(lines)


class Decl(object):
    """Represents a single documented declaration."""

    def __init__(self, com, decl):
        """Initialize a new documented declaration.

        Params:
          com: the raw text of the comment
          decl: the raw text of the declaration
        """
        lp = decl.find('(')
        if lp < 0:
            self.name = last_word(decl.rstrip(';'))
        else:
            self.name = last_word(decl[:lp])
        self.decl = ' '.join(decl.rstrip(';{').strip().split())
        self.comment = spc.sub('', com.rstrip())

    def __repr__(self):
        return '#Decl["%s"]' % self.decl

    def markdown(self):
        return '''------------
<a id="{name}"></a><pre>
{decl};
</pre>
{comment}
'''.format(name=self.name, decl=self.decl, comment=typeset(self.comment))


def parse_decls(text):
    """Parse a dictionary of declarations from text."""
    decls = collections.OrderedDict()
    for m in doc.finditer(text):
        d = Decl(m.group('text'), m.group('decl'))
        decls[d.name] = d
    return decls


def load_file(path):
    """Load declarations from path, or use cached results."""
    if path not in CACHE:
        with file(path, 'rU') as fp:
            CACHE[path] = parse_decls(fp.read())
    return CACHE[path]


def main(args):
    if len(args) != 2:
        print("Usage: mkdoc.py <input> <output", file=sys.stderr)
        sys.exit(1)

    doc_template = args[0]
    doc_markdown = args[1]

    with file(doc_template, 'rU') as input:
        template = input.read()

    with file(doc_markdown, 'wt') as output:
        pos = 0  # last position of input copied

        # Look for substitution markers in the template, and replace them with
        # their content.
        for ip in ins.finditer(template):
            output.write(template[pos:ip.start()])
            pos = ip.end()

            decls = load_file(ip.group('file'))
            if ip.group('names'):  # pick the selected names, in order
                decls = collections.OrderedDict(
                    (key, decls[key])
                    for key in ip.group('names').strip().split())

            # Render the selected declarations
            print(
                '<!-- begin generated section from "%s", '
                'DO NOT EDIT -->' % ip.group('file'),
                file=output)

            for decl in decls.values():
                print(decl.markdown(), file=output)

            print('<!-- end generated section -->', file=output)

        # Clean up any remaining template bits
        output.write(template[pos:])


if __name__ == "__main__":
    main(sys.argv[1:])
