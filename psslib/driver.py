#-------------------------------------------------------------------------------
# pss: driver.py
#
# Top-level functions and data used to execute pss.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import re
import sys

from .filefinder import FileFinder
from .contentmatcher import ContentMatcher
from .matchresult import MatchResult
from .defaultpssoutputformatter import DefaultPssOutputFormatter
from .utils import istextfile


TYPE_EXTENSION_MAP = {
        'actionscript':     ['.as', '.mxml'],
        'cc':               ['.c', '.h', '.xs'],
        'perl':             ['.pl', '.pm', '.pod', '.t'],
        'python':           ['.py'],
        'xml':              ['.xml', '.dtd', '.xslt', '.ent'],
}
ALL_KNOWN_EXTENSIONS = set(
        ext for extensions in TYPE_EXTENSION_MAP.itervalues() 
            for ext in extensions)

IGNORED_DIRS = set([   
    'autom4te.cache', 'blib', '_build', '.bzr', '.cdv', 'cover_db',
    'CVS', '_darcs', '~.dep', '~.dot', '.git', '.hg', '~.nib', 
    '.pc', '~.plst', 'RCS', 'SCCS', '_sgbak', '.svn'])

IGNORED_FILE_PATTERNS = set([r'~$', r'#.+#$', r'[._].*\.swp$', r'core\.\d+$'])


def pss_run(roots,
        pattern=None,
        output_formatter=None,
        only_find_files=False,
        search_all_types=False,
        search_all_files_and_dirs=False,
        add_ignored_dirs=[],
        remove_ignored_dirs=[],
        recurse=True,
        type_pattern=None, # for -G
        include_types=[],
        exclude_types=[],
        ignore_case=False,
        smart_case=False,
        invert_match=False,
        whole_words=False,
        literal_pattern=False,
        max_match_count=sys.maxint,
        do_colors=True,
        prefix_filename_to_file_matches=True,
        show_column_of_first_match=False,
        ):
    """ The main pss invocation function - handles all PSS logic.
        For documentation of options, see the --help output of the pss script,
        and study how its command-line arguments are parsed and passed to
        this function. Besides, most options are passed verbatim to submodules
        and documented there. I don't like to repeat myself too much :-)
    """
    # Set up a default output formatter, if none is provided
    #
    if output_formatter is None:
        output_formatter = DefaultPssOutputFormatter(
            do_colors,
            prefix_filename_to_file_matches,
            show_column_of_first_match)

    # Set up the FileFinder
    #
    if search_all_files_and_dirs:
        ignore_dirs = set()
    else:
        # gotta love set arithmetic
        ignore_dirs = ((IGNORED_DIRS | set(add_ignored_dirs))
                        - set(remove_ignored_dirs))

    search_extensions = set()
    ignore_extensions = set()
    search_file_patterns = set()
    ignore_file_patterns = set()

    if type_pattern is not None:
        search_file_patterns.add(type_pattern)
    elif not search_all_files_and_dirs and not search_all_types:
        if include_types:
            search_extensions.clear()
            for typ in include_types:
                search_extensions.update(TYPE_EXTENSION_MAP[typ])
        else:
            for ext in TYPE_EXTENSION_MAP.itervalues():
                search_extensions.update(ext)
        for typ in exclude_types:
            ignore_extensions.update(TYPE_EXTENSION_MAP[typ])
        ignore_file_patterns = IGNORED_FILE_PATTERNS
    else:
        # An empty search_extensions means all extensions are searched
        pass

    filefinder = FileFinder(
            roots=roots,
            recurse=recurse,
            ignore_dirs=ignore_dirs,
            search_extensions=search_extensions,
            ignore_extensions=ignore_extensions,
            search_file_patterns=search_file_patterns,
            ignore_file_patterns=ignore_file_patterns)

    # Set up the content matcher
    #

    if (    not ignore_case and 
            (smart_case and not _pattern_has_uppercase(pattern))):
        ignore_case = True

    matcher = ContentMatcher(
            pattern=pattern,
            ignore_case=ignore_case,
            invert_match=invert_match,
            whole_words=whole_words,
            literal_pattern=literal_pattern,
            max_match_count=max_match_count)

    # All systems go...
    #
    for filepath in filefinder.files():
        # If only_find_files is requested, this is kind of 'find -name'
        if only_find_files:
            output_formatter.found_filename(filepath)
            continue
        # The main path: do matching inside the file.
        # Some files appear to be binary - they are not of a known file type
        # an the heuristic istextfile says they're binary. For these files 
        # we try to find a single match and then simply report they're binary
        # files with a match. For other files, we let ContentMatcher do its
        # full work.
        #
        fileobj = open(filepath)
        if not _known_file_type(filepath) and not istextfile(fileobj):
            matches = list(matcher.match_file(fileobj, max_match_count=1))
            if matches:
                output_formatter.binary_file_matches(
                        'Binary file %s matches\n' % filepath)
            continue
        # istextfile does some reading on fileobj, so rewind it
        fileobj.seek(0)
        matches = list(matcher.match_file(fileobj))
        if not matches:
            # Nothing to see here... move along
            continue
        output_formatter.start_matches_in_file(filepath)
        for match in matches:
            output_formatter.matching_line(match)
        output_formatter.end_matches_in_file(filepath)


def _known_file_type(filename):
    """ Is the given file something we know about?
        Judges solely based on the file name and extension.
    """
    if os.path.splitext(filename)[1] in ALL_KNOWN_EXTENSIONS:
        return True
    else:
        return False


def _pattern_has_uppercase(pattern):
    """ Check whether the given regex pattern has uppercase letters to match
    """
    # Somewhat rough - check for uppercase chars not following an escape 
    # char (which may mean valid regex flags like \A or \B)
    skipnext = False
    for c in pattern:
        if skipnext:
            skipnext = False
            continue
        elif c == '\\': 
            skipnext = True
        else:
            if c >= 'A' and c <= 'Z':
                return True
    return False

    



