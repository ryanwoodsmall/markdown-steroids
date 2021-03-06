#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# mdx_steroids.md_mako

The `mdx_steroids.md_mako` feeds Markdown through the Mako templating system.

### Installation

```bash
pip install --user --upgrade git+https://github.com/twardoch/markdown-steroids.git
```

### Docs

* https://github.com/twardoch/markdown-steroids

### Options

```yaml
  mdx_steroids.md_mako:
    include_base    : '.'        # Default location from which to evaluate relative paths for the `<%include file="..."/>` statement.
    include_encoding: 'utf-8'    # Encoding of the files used by the `<%include file="..."/>` statement.
    include_auto    : 'head.md'  # Path to Mako file to be automatically included at the beginning.
    python_block    : 'head.py'  # Path to Python file to be automatically included at the beginning as a module block. Useful for global imports and functions.
    meta:                        # Dict of args passed to `mako.Template().render()`. Can be overriden through Markdown YAML metadata.
      author        : 'John Doe' # Can be referred inside the Markdown via `${author}`
      status        : 'devel'    # Can be referred inside the Markdown via `${status}`
```

### Example

This assumes that the `meta` or `mdx_steroids.meta_yaml` extension is enabled,
so parsing metadata at the beginning of the file works.

#### Input Markdown

```markdown
---
author: John Doe
---
<%!
import datetime
def today():
    now = datetime.datetime.now()
    return now.strftime('%Y-%m-%d')
%>

${author} has last edited this on ${today()}.

% for number in ['one', 'two', 'three']:
* ${number}
% endfor
```

#### Output HTML

<p>John Doe has last edited this on 2017-08-17.</p>
<ul>
<li>one</li>
<li>two</li>
<li>three</li>
</ul>

```html
<p>John Doe has last edited this on 2017-08-17.</p>
<ul>
<li>one</li>
<li>two</li>
<li>three</li>
</ul>
```

Copyright (c) 2017 Adam Twardoch <adam+github@twardoch.com>
License: [BSD 3-clause](https://opensource.org/licenses/BSD-3-Clause)
"""

__version__ = '0.5.0'

import os.path
import io
import re
from markdown import Extension
from markdown.preprocessors import Preprocessor
from mako.template import Template
from mako.lookup import TemplateLookup


class MakoPreprocessor(Preprocessor):
    # Mako interprets `##` at the beginning of a line as a comment,
    # while in Markdown it’s the H2 heading. Therefore, before
    # passing the content to Mako, we replace the initial `##`
    # with a fake string, and after the Mako processing
    # we change it back.
    MD_HEAD_BEFORE_MAKO = u'##'
    RE_MD_HEAD_BEFORE_MAKO = re.compile(u'^' + MD_HEAD_BEFORE_MAKO)
    MD_HEAD_AFTER_MAKO = u'3fHkslFJ39Z' # This is the fake string
    RE_MD_HEAD_AFTER_MAKO = re.compile(u'^' + MD_HEAD_AFTER_MAKO)

    def __init__(self, config, md):
        super(MakoPreprocessor, self).__init__(md)
        self.mako_args = config.get('meta')
        self.mako_include_base = config.get('include_base')
        self.mako_include_encoding = config.get('include_encoding')
        self.mako_include_auto = config.get('include_auto')
        self.mako_python_block = config.get('python_block')
        if type(self.mako_include_base) is list:
            self.mako_base_dirs = self.mako_include_base
        else:
            self.mako_base_dirs = [self.mako_include_base]

    def run(self, lines):
        lines = [re.sub(self.RE_MD_HEAD_BEFORE_MAKO, self.MD_HEAD_AFTER_MAKO, line) for line in lines]
        if self.mako_python_block:
            path_python_block = None
            if os.path.exists(self.mako_python_block):
                path_python_block = self.mako_python_block
            elif os.path.exists(os.path.join(self.mako_include_base[0], self.mako_python_block)):
                path_python_block = os.path.join(self.mako_include_base[0], self.mako_python_block)
            if path_python_block:
                with io.open(path_python_block, 'r', encoding='utf8') as f:
                    python_block = f.read().splitlines()
                lines = [u'<%!'] + python_block + [u'%>'] + lines
        else:
            lines = [u''] + lines
        if self.mako_include_auto:
            line_include_auto = u'<%include file="{}"/>'.format(self.mako_include_auto)
            lines = [line_include_auto] + lines
        md = u"\n".join(lines)
        mako_args = self.mako_args
        if hasattr(self.markdown, 'Meta'):
            md_meta = {k.lower(): u''.join(v) if isinstance(v, list) else v for k, v in self.markdown.Meta.items()}
            assert isinstance(mako_args, dict)
            mako_args.update(md_meta)
        mako_lookup = TemplateLookup(directories=self.mako_base_dirs)
        mako_tpl = Template(md, input_encoding=self.mako_include_encoding, lookup=mako_lookup)
        mako_result = mako_tpl.render(**mako_args)
        lines = mako_result.splitlines()[1:]
        lines = [re.sub(self.RE_MD_HEAD_AFTER_MAKO, self.MD_HEAD_BEFORE_MAKO, line) for line in lines]
        return lines


class MarkdownMakoExtension(Extension):
    def __init__(self, *args, **kwargs):
        self.config = {
            'include_base'    : [u'.', 'Default location from which to evaluate ' \
                                           'relative paths for the <%include file="..."/> statement.'],
            'include_encoding': ['utf-8', 'Encoding of the files used by the <%include file="..."/> statement.'],
            'include_auto'    : [u'', 'Path to Mako file to be automatically included at the beginning.'],
            'python_block'    : [u'', 'Path to Python file to be automatically' \
                                            'included at the beginning as a module block.'],
            'meta'            : [{}, 'Dict of args passed to mako.Template().render().' \
                                            'Can be overriden through Markdown YAML metadata.'],
        }
        super(MarkdownMakoExtension, self).__init__(*args, **kwargs)

    def extendMarkdown(self, md):
        self.md = md
        md.registerExtension(self)
        config = self.getConfigs()
        md_mako = MakoPreprocessor(config, md)
        md.preprocessors.register(md_mako, 'md_mako', ">normalize_whitespace")

def makeExtension(*args, **kwargs):
    return MarkdownMakoExtension(*args, **kwargs)
