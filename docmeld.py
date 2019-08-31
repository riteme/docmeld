#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

__VERSION__ = 'v0.1.1'

FILESIZE_LIMIT = 32 * 1024  # 32KB

DISABLE_CACHE = False
DISABLE_DEBUG = True

PREFERENCE_MODULE = 'preferences'

GIT_EXECUTABLE = '/usr/bin/git'
GIT_REPO_DIRECTORY = 'cloned'
GIT_URL_START = 'git+'
GIT_DEFAULT_BRANCH = 'master'

SYSTEM_LIBCLANG = []
LIBCLANG_NO_USER_SPECIFIED = False
LIBCLANG_PRIORITIZE_USER_CONFIG = True
LIBCLANG_SEARCH_BY_LOCATE = True

import os
import os.path
import sys
import re
import json
import fnmatch
import argparse
import hashlib
import shutil
import importlib
import subprocess

import itertools
zip = itertools.izip

try:
    import cPickle as pickle
except:
    import pickle

from sys import argv
from colorama import Fore
from collections import defaultdict, namedtuple

config = None

# Logging
def INFO(message):
    if type(message) is unicode:
        message = message.encode('utf-8')
    if sys.stdout.isatty():
        print('%s(info)%s %s' % (Fore.GREEN, Fore.RESET, message))
    else:
        print('(info) %s' % message)
    sys.stdout.flush()
def WARN(message):
    if type(message) is unicode:
        message = message.encode('utf-8')
    if sys.stderr.isatty():
        print('%s(warn)%s %s' % (Fore.YELLOW, Fore.RESET, message), file=sys.stderr)
    else:
        print('(warn) %s' % message)
    sys.stderr.flush()
def ERROR(message):
    if type(message) is unicode:
        message = message.encode('utf-8')
    if sys.stderr.isatty():
        print('%s(ERROR)%s %s' % (Fore.RED, Fore.RESET, message), file=sys.stderr)
    else:
        print('(ERROR) %s' % message)
    sys.stderr.flush()
def DEBUG(message):
    global DISABLE_DEBUG

    if not DISABLE_DEBUG:
        if type(message) is unicode:
            message = message.encode('utf-8')
        if sys.stdout.isatty():
            print('%s(debug)%s %s' % (Fore.BLUE, Fore.RESET, message))
        else:
            print('(debug) %s' % message)
        sys.stdout.flush()

# Utilities
def sh(command):
    result = os.system(command)
    DEBUG('"%s" ⇒ %s' % (command, result))
    return result

def md5(x):
    if type(x) is unicode:
        x = x.encode('utf-8')
    return hashlib.md5(x).hexdigest()

def checksum(signature, content):
    method, digest = signature.split('=', 1)
    if method not in hashlib.algorithms_available:
        ERROR('Failed to examine checksum "%s": unsupported hash algorithm.' % signature)
        return False
    if type(content) is unicode:
        content = content.encode('utf-8')
    evaluated = hashlib.new(method, string=content).hexdigest()
    # DEBUG('evaluated = %s' % evaluated)
    return digest == evaluated

# Ignores
def ignored(path):
    def _matched(m, s):
        r = m.match(s)
        return r and r.end() == len(s)
    basename = os.path.basename(path)
    for m in config.IGNORES:
        if _matched(m, basename) or _matched(m, path):
            return True
    return False

# Cache Management
def load_cache(content, name):
    global DISABLE_CACHE

    if type(content) is unicode:
        content = content.encode(config.ENCODING)
    if type(name) is unicode:
        name = name.encode(config.PATH_ENCODING)
    key = md5(name + content)
    if not os.path.exists(config.CACHE_DIRECTORY):
        os.makedirs(config.CACHE_DIRECTORY)
    path = os.path.join(config.CACHE_DIRECTORY, key)
    return (path, False if DISABLE_CACHE else os.path.exists(path))

# Basic Git manipulations
def git_clone(url, dest):
    INFO('Cloning repository "%s"...' % url)
    return sh('%s clone %s %s' % (GIT_EXECUTABLE, url, dest))

def git_has_branch(branch):
    result = subprocess.check_output([GIT_EXECUTABLE, 'branch', '-l', '-a']).strip().split('\n')
    li = [x.rsplit('/', 1)[-1] for x in result]
    return branch in li

def git_create_branch(branch):
    return sh('%s branch %s' % (GIT_EXECUTABLE, branch))

def git_checkout(branch):
    INFO('Checking out branch "%s"...' % branch)
    return sh('%s checkout %s -q' % (GIT_EXECUTABLE, branch))

def git_pull(branch):
    INFO('Pulling data of branch "%s" from remote...' % branch)
    return sh('%s pull origin %s' % (GIT_EXECUTABLE, branch))

def git_get_head_sha1():
    result = subprocess.check_output([GIT_EXECUTABLE, 'rev-parse', 'HEAD']).strip()
    DEBUG('Current HEAD: %s' % result)
    return result

def handle_git_url(url, branch, head):
    ERROR_CODE = 8
    url = url[len(GIT_URL_START):]
    folder = os.path.join(GIT_REPO_DIRECTORY, md5(url))
    DEBUG('Repository saved to "%s".' % folder)
    updated = False
    if not os.path.exists(folder):
        if git_clone(url, folder) != 0:
            ERROR('Unable to clone the repo "%s".' % url)
            exit(ERROR_CODE)
        updated = True
    cwd = os.getcwd()
    os.chdir(folder)
    # DEBUG(os.path.abspath(folder))
    if not git_has_branch(branch):
        ERROR('No branch named "%s" found.')
        exit(ERROR_CODE)
    if git_checkout(branch) != 0:
        ERROR('Unable to checkout the branch "%s".' % branch)
        exit(ERROR_CODE)
    if not updated and git_pull(branch) != 0:
        ERROR('Unable to pull from remote on branch "%s".' % branch)
        exit(ERROR_CODE)
    if head is not None and head not in git_get_head_sha1():
        WARN('Unexpected HEAD commit.')
        exit(0)
    os.chdir(cwd)
    return folder

# Python Markdown
import markdown, re
import markdown.extensions.codehilite
from markdown import Extension
from markdown.inlinepatterns import \
    LinkPattern, ReferencePattern, AutolinkPattern, AutomailPattern, \
    LINK_RE, REFERENCE_RE, SHORT_REF_RE, AUTOLINK_RE, AUTOMAIL_RE
from markdown.inlinepatterns import SimpleTagPattern
from markdown.postprocessors import Postprocessor

# LaTeX Extension
# oh-my-acm.latex
class MathJaxPattern(markdown.inlinepatterns.Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(
            self,
            r'(?<!\\)(\$\$?)(.+?)\2'
        )

    def handleMatch(self, m):
        node = markdown.util.etree.Element('tex')
        node.text = markdown.util.AtomicString(
            m.group(2) + m.group(3) + m.group(2))
        return node

class MathJaxExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add('tex', MathJaxPattern(), '<escape')

def markdown_latex(configs=[]):
    return MathJaxExtension(configs)

# Tasklist Extension
# oh-my-acm.tasklist
class ChecklistExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.postprocessors.add('checklist', ChecklistPostprocessor(md),
                              '>raw_html')

class ChecklistPostprocessor(Postprocessor):
    pattern = re.compile(r'<li>\[([ Xx])\]')

    def run(self, html):
        html = re.sub(self.pattern, self._convert_checkbox, html)
        before = '<ul>\n<li><input type="checkbox"'
        after = before.replace('<ul>', '<ul class="checklist">')
        return html.replace(before, after)

    def _convert_checkbox(self, match):
        state = match.group(1)
        checked = ' checked' if state != ' ' else ''
        return '<li><input type="checkbox" disabled%s>' % checked

def markdown_tasklist(configs=None):
    if configs is None:
        return ChecklistExtension()
    else:
        return ChecklistExtension(configs=configs)

# DelIns Extension
# oh-my-acm.delins
class DelInsExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md, md_globals):
        DEL_RE = r"(\~\~)(.+?)(\~\~)"
        INS_RE = r"(\+\+)(.+?)(\+\+)"
        md.inlinePatterns.add(
            'del', SimpleTagPattern(DEL_RE, 'del'), '<not_strong')
        md.inlinePatterns.add(
            'ins', SimpleTagPattern(INS_RE, 'ins'), '<not_strong')

def markdown_delins(configs={}):
    return DelInsExtension(configs=dict(configs))

# Initialize Markdown & C++ Parser according to preferences
md = None
clang = None
cl = None
def initialize_parsers():
    global md
    global clang
    global cl
    global SYSTEM_LIBCLANG

    INFO('Loading Python Markdown...')
    for i in xrange(len(config.MARKDOWN_EXTENSIONS)):
        ext = config.MARKDOWN_EXTENSIONS[i]
        if type(ext) == str and ext.startswith('oh-my-acm'):
            ext = ext.split('.', 1)[1]
            config.MARKDOWN_EXTENSIONS[i] = eval('markdown_%s()' % ext)
    md = markdown.Markdown(extensions=config.MARKDOWN_EXTENSIONS)

    # Clang
    import clang.cindex
    if not LIBCLANG_NO_USER_SPECIFIED:
        if LIBCLANG_PRIORITIZE_USER_CONFIG:
            SYSTEM_LIBCLANG = [config.LIBCLANG_PATH] + SYSTEM_LIBCLANG
        else:
            SYSTEM_LIBCLANG.append(config.LIBCLANG_PATH)
    if LIBCLANG_SEARCH_BY_LOCATE:
        try:
            result = subprocess.check_output(['locate', 'libclang.so']).strip()
            SYSTEM_LIBCLANG += [x.strip() for x in result.split('\n')]
        except:
            WARN('"locate" found no "libclang.so" file.')
    DEBUG(SYSTEM_LIBCLANG)
    for path in SYSTEM_LIBCLANG:
        if os.path.isfile(path):
            DEBUG('Try loading libclang ("%s")...' % path)
            try:
                clang.cindex.Config.set_library_file(path)
                cl = clang.cindex.Index.create()
            except:
                DEBUG('Failed to load "%s".' % path)
                cl = None
            else:
                INFO('"%s" loaded.' % path)
                break
    if cl is None:
        ERROR('Failed to load libclang.')
        exit(16)

    INFO('Loading C++ Parser...')
    config.SPECIAL_MAP = {}
    for key, li in config.SPECIAL.items():
        for value in li:
            config.SPECIAL_MAP[value] = key

# C++ Parser
def get_tag(token):
    NONE = -1
    NON_ASCII = 1
    ASCII = 0
    def get_type(c):
        if ord(c) > 255:
            return NON_ASCII
        return ASCII

    tags = (token.spelling or token.displayname).decode('utf-8').split('\n')
    for i in xrange(len(tags)):
        last = NONE
        ret = []
        for c in tags[i]:
            t = get_type(c)
            if t != last:
                if t == NON_ASCII:
                    ret.append(config.TAG_BEGIN.format(name=config.NON_ASCII_CLASS))
                elif last != NONE:
                    ret.append(config.TAG_END)
            if c in config.REPLACEMENT:
                ret.append(config.REPLACEMENT[c])
            else:
                ret.append(c)
            last = t
        if last == NON_ASCII:
            ret.append(config.TAG_END)
        tags[i] = ''.join(ret)

    return tags

def parse_cxx(path, dirname):
    if sys.stderr.isatty():
        SEVERITY_NAME = {
            clang.cindex.Diagnostic.Ignored: 'IGN',
            clang.cindex.Diagnostic.Note: 'NOTE',
            clang.cindex.Diagnostic.Warning: Fore.YELLOW + 'WARN' + Fore.RESET,
            clang.cindex.Diagnostic.Error: Fore.RED + 'ERROR' + Fore.RESET,
            clang.cindex.Diagnostic.Fatal: Fore.RED + 'FATAL' + Fore.RESET
        }
    else:
        SEVERITY_NAME = {
            clang.cindex.Diagnostic.Ignored: 'IGN',
            clang.cindex.Diagnostic.Note: 'NOTE',
            clang.cindex.Diagnostic.Warning: 'WARN',
            clang.cindex.Diagnostic.Error: 'ERROR',
            clang.cindex.Diagnostic.Fatal: 'FATAL'
        }

    INFO('Parsing "%s"...' % path)
    with open(path, 'r') as reader:
        content = reader.read()
    cache, flag = load_cache(content, path)
    if flag:
        DEBUG('"%s" cached.' % path)
        with open(cache, 'r') as reader:
            return pickle.load(reader)

    DEBUG('Options: %s' % ' '.join(config.CLANG_ARGS))
    lines = content.split('\n')
    tu = cl.parse(
        path, config.CLANG_ARGS,
        options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
    )
    diag = list(tu.diagnostics)
    if len(diag):
        for msg in diag:
            WARN('[%s][%s: %s:%s] %s' % (
                SEVERITY_NAME[msg.severity],
                msg.location.file, msg.location.line, msg.location.column,
                msg.spelling
            ))
        WARN('Diagnostics ignored. Processing will continue.')

    DEBUG('Generating HTML...')
    line, column = 1, 1
    buf = []
    for token in tu.get_tokens(extent=tu.cursor.extent):
        loc = token.location
        while loc.line != line:
            # Sometimes clang will ignore line breaks "\" at the end of each line
            # trailing spaces trimmed
            buf.append(lines[line - 1][column - 1:].rstrip() + '\n')
            line += 1
            column = 1
        if loc.column != column:
            tab_count = lines[line - 1][column - 1 : loc.column - 1].count('\t')
            length = loc.column - column
            buf.append(' ' * ((length - tab_count) + tab_count * config.TABSIZE))
            column = loc.column

        tags = get_tag(token)
        #DEBUG(tags)
        classes = []
        if token.kind == clang.cindex.TokenKind.KEYWORD:
            classes.append(config.KEYWORD_CLASS)
        if token.kind == clang.cindex.TokenKind.IDENTIFIER:
            classes.append(config.IDENTIFIER_CLASS)
        if token.kind == clang.cindex.TokenKind.COMMENT:
            classes.append(config.COMMENT_CLASS)
        if token.kind == clang.cindex.TokenKind.LITERAL:
            classes.append(config.LITERAL_CLASS)
        if token.kind == clang.cindex.TokenKind.PUNCTUATION:
            classes.append(config.PUNCTUATION_CLASS)
        if len(tags) == 1 and tags[0] in config.SPECIAL_MAP:
            classes.append(config.SPECIAL_MAP[tags[0]])

        for i in xrange(len(tags)):
            tags[i] = '%s%s%s' % (
                config.TAG_BEGIN.format(name=' '.join(classes)),
                tags[i], config.TAG_END
            )
        buf.append('\n'.join(tags))

        line = token.extent.end.line
        column = token.extent.end.column
    # Includes tailing contents
    if column != len(lines[line - 1]):
        buf.append(lines[line - 1][column - 1:].rstrip())

    DEBUG('Parsing metainfo...')
    data = list(itertools.islice(tu.get_tokens(extent=tu.cursor.extent), 1))[0]
    meta = {}
    meta_end = 1
    if data.kind == clang.cindex.TokenKind.COMMENT and data.spelling.startswith('/**'):
        meta_end = data.extent.end.line + 1
        data = data.spelling.split('\n')[1:-1]
        for row in data:
            key, value = row.split(':', 1)
            key = key.strip('\* ')
            value = value.strip()
            meta[key] = value.decode(config.ENCODING)
    DEBUG('Parsing file name...')
    name = os.path.basename(os.path.splitext(path)[0])
    vals = name.split(config.NAMEMETA_SEPARATER)
    for key, val in zip(config.NAMEMETA_KEYS, vals):
        if key not in meta:
            meta[key] = val.strip().decode(config.ENCODING)
    # Default to match title with description file
    if config.META_DESCRIPTION not in meta:
        title = meta[config.META_TITLE]
        for ext in config.DESCRIPTION_EXTENSIONS:
            desc = title + ext
            desc_path = os.path.join(dirname, desc)
            DEBUG('Try "%s"...' % desc_path)
            if os.path.isfile(desc_path):
                break
            else:
                desc = None
        if desc is not None:
            DEBUG('Matched "%s".' % desc)
            meta[config.META_DESCRIPTION] = desc

    DEBUG('Generating slices...')
    last = 0
    slices = []
    for cur in tu.cursor.get_children():
        pos = cur.location.line
        if cur.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
            if cur.spelling == config.BLOCK_BEGIN_MARCO:
                if last:
                    WARN('[L%s] Duplicated block beginning. Ignored.' % pos)
                else:
                    last = pos + 1
            elif cur.spelling == config.BLOCK_END_MARCO:
                if last:
                    slices.append((last, pos))
                    last = 0
                else:
                    WARN('[L%s] Unmatched block ending. Ignored.' % pos)
    if last:
        WARN('[L%s] Unmatched block beginning. Default to file end [L%s].' % (last, line))
        slices.append((last, line + 1))
    if len(slices) == 0:
        DEBUG('No specific range. Default is the entire file.')
        slices = [(meta_end, line + 1)]

    result = (''.join(buf), meta, slices)
    with open(cache, 'w') as writer:
        pickle.dump(result, writer)
    return result

def add_line_numbers(s, slices):
    data = ['<div class="%s"><div class="%s">%%s</div><div class="%s">%s</div></div>' %
        (config.LINE_CLASS, config.LINE_NUMBER_CLASS, config.CODE_CLASS, code.replace('%', '%%'))
        for code in s.split('\n')]
    output = []
    line = 0
    for l, r in slices:
        for i in xrange(l - 1, r - 1):
            line += 1
            output.append(data[i] % line)

    return ('<div class="%s">' % config.CODE_BLOCK_CLASS) + '\n'.join(output) + '</div>'

# Markdown Parser
def parse_markdown(path, dirname):
    DEBUG('Parsing markdown file: %s' % path)
    with open(path, 'r') as reader:
        content = reader.read()
    cache, flag = load_cache(content, path)
    if flag:
        DEBUG('"%s" cached.' % path)
        with open(cache, 'r') as reader:
            return pickle.load(reader)
    result = md.convert(content.decode(config.ENCODING))
    with open(cache, 'w') as writer:
        pickle.dump(result, writer)
    return result

# Resolver
def resolve(path, dirname):
    code, meta, slices = parse_cxx(path, dirname)

    DEBUG('Metainfo:')
    for item in meta.items():
        DEBUG('"%s": "%s"' % item)

    # Describing one document
    code = add_line_numbers(code, slices)
    desc_path = os.path.relpath(os.path.join(dirname, meta[config.META_DESCRIPTION])) if config.META_DESCRIPTION in meta else None
    desc = parse_markdown(desc_path, dirname) if desc_path else ''
    title = meta[config.META_TITLE] if config.META_TITLE in meta else config.META_DEFAULT_TITLE
    category = meta[config.META_CATEGORY] if config.META_CATEGORY in meta else config.META_DEFAULT_CATEGORY
    rank = int(meta[config.META_RANK]) if config.META_RANK in meta else config.META_DEFAULT_RANK
    return namedtuple(
        'Item', ['desc', 'desc_path', 'code', 'title', 'category', 'rank', 'path', 'meta']
    )(desc, desc_path, code, title, category, rank, path, meta)

# Main
def main():
    global config
    global DISABLE_CACHE
    global DISABLE_DEBUG

    parser = argparse.ArgumentParser(description='(docmeld %s) A generic document compiler for ICPC-related contests. Utilized by Fudan U2 in Fall 2019.' % __VERSION__)
    parser.add_argument('LOCATION', help='path to the root directory of documents or URL to a git repository in "%s<URL>" format.' % GIT_URL_START)
    parser.add_argument('-o', '--output', help='location to place the generated HTML file.')
    parser.add_argument('-b', '--branch', help='specify the branch of the git repository.')
    parser.add_argument('-c', '--checksum-list', help='examine the checksums of specified files provided by a JSON file for security. JSON format: {"path_to_file": "sha256=...", ...}')
    parser.add_argument('-s', '--head-sha1', help='examine the SHA1 hash code to current HEAD.')
    parser.add_argument('-n', '--no-cache', action='store_true', help='disable cache and force full re-generation.')
    parser.add_argument('-v', '--verbose', action='store_true', help='show more messages.')
    parser.add_argument('-q', '--quiet', action='store_true', help='show less messages.')
    args = parser.parse_args()

    if args.no_cache:
        DISABLE_CACHE = True
    if args.verbose:
        DISABLE_DEBUG = False
    if args.quiet:
        DISABLE_DEBUG = True
    if args.verbose and args.quiet:
        WARN('Both "-q" and "-v" are enabled. Default to be quiet.')
    output_path = None
    if args.output:
        output_path = os.path.abspath(args.output)

    # Handle URL (local/git)
    if args.LOCATION.startswith(GIT_URL_START):
        if args.branch is None:
            args.branch = GIT_DEFAULT_BRANCH
        root_directory = handle_git_url(args.LOCATION, args.branch, head=args.head_sha1)
    else:
        if not os.path.isdir(args.LOCATION):
            ERROR('Failed to open directory "%s"' % args.LOCATION)
            exit(1)
        root_directory = args.LOCATION

    # Load checksum list (JSON format)
    checksum_list = {}
    if args.checksum_list is not None:
        if not os.path.exists(args.checksum_list):
            ERROR('Checksum list "%s" not found. Please ensure this file exists.' % args.checksum_list)
            exit(233)
        with open(args.checksum_list) as reader:
            checksum_list = json.load(reader)

    root_directory = os.path.abspath(root_directory)
    os.chdir(root_directory)
    # Examine checksums (especially for preferences.py)
    try:
        for path, sig in checksum_list.items():
            if not os.path.isfile(path):
                WARN('File "%s" does not exist. No checksum was examined for this file.' % path)
            else:
                with open(path, 'r') as reader:
                    if not checksum(sig, reader.read()):
                        ERROR('Decline to compile the project: file "%s" does not pass the checksum examination.' % path)
                        exit(2333)
    except Exception as e:
        ERROR('An error occurred during checksum examination. [%s] %s' % (type(e), e))
        exit(444)

    # Load preferences
    sys.path.append(root_directory)
    try:
        config = importlib.import_module(PREFERENCE_MODULE)
    except ImportError:
        ERROR('No preference file was found. Please ensure that there is a "preferences.py" in your project directory.')
        exit(2)

    # Compile ignorement rules
    config.IGNORES = [re.compile(fnmatch.translate(x)) for x in config.IGNORES]

    # Scan all files
    file_list = []  # (dirname, path, ext)
    for dirpath, dnames, fnames in os.walk(root_directory, followlinks=True):
        # Skip hidden files & directories
        dnames[:] = [x for x in dnames if not x.startswith('.')]
        fnames[:] = [x for x in fnames if not x.startswith('.')]
        dirname = os.path.relpath(dirpath, start=root_directory)
        for name in fnames:
            path = os.path.relpath(os.path.join(dirpath, name), start=root_directory)
            if ignored(path):
                DEBUG('"%s" ignored due to IGNORES list.' % path)
            else:
                statinfo = os.stat(path)
                if statinfo.st_size <= FILESIZE_LIMIT:
                    _, ext = os.path.splitext(path)
                    if ext in config.FILE_EXTENSIONS or ext in config.DESCRIPTION_EXTENSIONS:
                        file_list.append((dirname, path, ext))
                else:
                    DEBUG('"%s" ignored due to file size limitation.' % path)

    initialize_parsers()
    database = defaultdict(list)
    used_documents = set()

    # Process source code
    for dirname, path, ext in file_list:
        if ext not in config.FILE_EXTENSIONS:
            continue
        result = resolve(path, dirname)
        if result.desc_path:
            used_documents.add(result.desc_path)
        database[result.category].append(result)

    INFO('Concatenating documents...')
    cnt = 0
    toc = []
    body = []
    for category, docs in database.items():
        DEBUG('Processing category "%s"...' % category)
        toc.append(config.TOC_CATEGORY_TEMPLATE.format(category=category, category_md5=md5(category)))
        for doc in sorted(docs, key=lambda doc: (doc.rank, doc.title)):
            cnt += 1
            toc.append(config.TOC_TITLE_TEMPLATE.format(id=cnt, title=doc.title))
            body.append(config.DOCUMENT_TEMPLATE.format(
                id=cnt, title=doc.title, category=doc.category, category_md5=md5(doc.category),
                path=doc.path.decode(config.PATH_ENCODING), description=doc.desc, code=doc.code))

    toc.append(config.TOC_CATEGORY_TEMPLATE.format(
        category=config.META_DOCUMENT_DEFAULT_CATEGORY,
        category_md5=md5(config.META_DOCUMENT_DEFAULT_CATEGORY)))
    body.append(config.PAGE_SEPARATOR)

    # Scan unused documents
    for dirname, path, ext in file_list:
        if ext not in config.DESCRIPTION_EXTENSIONS or path.decode(config.PATH_ENCODING) in used_documents:
            continue
        body.append(config.UNUSED_DOCUMENT_TEMPLATE.format(
            title=path.decode(config.PATH_ENCODING), description=parse_markdown(path, dirname)))

    if output_path is None:
        output_path = os.path.abspath(config.OUTPUT_PATH)
    output_folder = os.path.dirname(output_path)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    DEBUG('Writing into "%s"...' % output_path)
    with open(output_path, 'w') as writer:
        data = config.WEBPAGE_TEMPLATE.format(
            document_title=config.DOCUMENT_TITLE,
            document=config.CONTENT_TEMPLATE.format(
                toc='\n'.join(toc),
                separator=config.PAGE_SEPARATOR,
                document='\n'.join(body)
        ))
        writer.write(data.encode(config.ENCODING))

    DEBUG('Copying assets into "%s"...' % (output_folder))
    for name in config.ASSETS:
        path = os.path.join(output_folder, name)
        if os.path.exists(path) and os.path.samefile(name, path):
            DEBUG('"%s" skipped.' % name)
            continue
        if os.path.isfile(name):
            DEBUG('Copy file "%s"...' % name)
            folder = os.path.dirname(path)
            if not os.path.exists(folder):
                os.makedirs(folder)
            shutil.copyfile(name, path)
        elif os.path.isdir(name):
            DEBUG('Copy directory "%s"...' % name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            shutil.copytree(name, path)
        else:
            WARN('File or directory "%s" does not exist. Ignored.' % name)

if __name__ == "__main__":
    main()
