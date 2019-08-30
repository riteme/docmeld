# -*- coding: utf-8 -*-

# Project Setting
DOCUMENT_TITLE = "Reference Document"
OUTPUT_PATH = 'output.html'
ASSETS = ['style.css']
IGNORES = ['README.md', 'readme.md']

# Clang Settings
LIBCLANG_PATH = '/usr/lib/llvm-6.0/lib/libclang.so.1'
CLANG_ARGS = ['-std=c++14', '-x', 'c++']

# CSS Settings
CODE_BLOCK_CLASS = 'code-block'
LINE_CLASS = 'line'
LINE_NUMBER_CLASS = 'number'
CODE_CLASS = 'code'
TAG_BEGIN = '<span class="{name}">'
TAG_END = '</span>'
KEYWORD_CLASS = 'keyword'
IDENTIFIER_CLASS = 'ident'
COMMENT_CLASS = 'comment'
LITERAL_CLASS = 'literal'
PUNCTUATION_CLASS = 'punct'
NON_ASCII_CLASS = 'non-ascii'
SPECIAL = {
    'pod': [
        'bool', 'char', 'short', 'int', 'long', 'signed', 'unsigned',
        'float', 'double', 'void', 'wchar', 'size_t', '__int128_t',
        'char16_t'
    ],
    'preprocessor': [
        'include', 'define', 'undef', 'pragma', 'if', 'else', 'elif', 'endif',
        'ifdef', 'ifndef'
    ],
    'simple-variable': list('abcdefghlpqrstuvwxyz')
}

# Makrdown Settings
MARKDOWN_EXTENSIONS = [
    'markdown.extensions.fenced_code',
    'markdown.extensions.footnotes',
    'markdown.extensions.tables',
    'markdown.extensions.toc',
    'markdown.extensions.smart_strong',
    'markdown.extensions.attr_list',
    'markdown.extensions.nl2br',
    'markdown.extensions.meta',
    #'markdown.extensions.smarty',
    'oh-my-acm.latex',
    'oh-my-acm.tasklist',
    'oh-my-acm.delins'
]

# Metainfo Settings
META_TITLE = u'title'
META_CATEGORY = u'category'
META_DESCRIPTION = u'description'
META_RANK = u'rank'
META_DEFAULT_TITLE = u'Untitled'
META_DEFAULT_CATEGORY = u'UNCLASSIFIED'
META_DOCUMENT_DEFAULT_CATEGORY = u'OTHER DOCUMENTS'
META_DEFAULT_RANK = 0

# Filename-Generated Metainfo Settings
NAMEMETA_SEPARATER = '，'
NAMEMETA_KEYS = [META_TITLE, META_CATEGORY]

# Source File Settings
FILE_EXTENSIONS = ['.cpp', '.c', '.cxx']
DESCRIPTION_EXTENSIONS = ['.md', '.mkd', '.markdown']
ENCODING = 'utf-8'
PATH_ENCODING = 'utf-8'
TABSIZE = 2

# Display Settings
REPLACEMENT = {
    '<': '&lt;',
    '>': '&gt;',
    '&': '&amp;',
}

# Generator Settings
CACHE_DIRECTORY = '.cache'
BLOCK_BEGIN_MARCO = 'ACM_BEGIN'
BLOCK_END_MARCO = 'ACM_END'

# Document Settings
def from_file(path):
    with open(path, 'r') as reader:
        return reader.read().decode(ENCODING)

CONTENT_TEMPLATE = u'<div class="toc">{toc}</div>{separator}{document}'
TOC_CATEGORY_TEMPLATE = u'<h3 id="{category_md5}"><div class="left">{category}</div><div class="right">□</div></h3>'
TOC_TITLE_TEMPLATE = u'<h4 class="title"><b><a href="#{id}">{id}</a></b>. {title}</h4>'
DOCUMENT_TEMPLATE = u'''<div class="source-code">
<h4 id="{id}"><div class="left">
<b><a href="#{category_md5}">{id}</a>.</b><div class="document-title">{title}</div>
<div class="document-path">[{path}]</div></div>
<div class="right">■</div></h4>
{description}
{code}</div>'''
UNUSED_DOCUMENT_TEMPLATE = u'''<div class="document">
<h6><div class="left">∘ <code>{title}</code></div><div class="right">■</div></h6>
<div>{description}</div></div>
'''
PAGE_SEPARATOR = u'<hr />'

# Using KaTeX v0.11.0
WEBPAGE_TEMPLATE = u'''<!DOCTYPE html><html><head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.11.0/dist/katex.min.css" integrity="sha384-BdGj8xC2eZkQaxoQ8nSLefg4AV4/AwB3Fj+8SUSo7pnKP6Eoy18liIKTPn9oBYNG" crossorigin="anonymous">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.11.0/dist/katex.min.js" integrity="sha384-JiKN5O8x9Hhs/UE5cT5AAJqieYlOZbGT3CHws/y97o3ty4R7/O5poG9F3JoiOYw1" crossorigin="anonymous"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.11.0/dist/contrib/auto-render.min.js" integrity="sha384-kWPLUVMOks5AQFrykwIup5lo0m3iMkkHrD0uJ4H5cjeGihAutqP0yW0J6dpFiVkI" crossorigin="anonymous"
    onload="renderMathInElement(document.body, options={{delimiters: [{{ left: '$$', right: '$$', display: true }}, {{ left: '$', right: '$', display: false }}]}})"></script>
  <link rel="stylesheet" type="text/css" href="style.css">
  <title>{document_title}</title>
</head><body>
{document}
</body></html>
'''
