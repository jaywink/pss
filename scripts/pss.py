#!/usr/bin/env python
#-------------------------------------------------------------------------------
# pss: pss.py
#
# Top-level script
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import optparse

# Make sure we can import psslib, even if run from the source distribution
# root or its scripts/ dir
try:
    import psslib
except ImportError:
    sys.path.extend(['.', '..'])

from psslib import __version__
from psslib.driver import pss_run, TYPE_EXTENSION_MAP


def main():
    options, args, optparser = parse_cmdline(sys.argv[1:])

    # find_files_matching_pattern means both find_files and sets
    # the type_pattern. This is handled here because find_files affects
    # the verification of len(args) later.
    #
    if options.find_files_matching_pattern is not None:
        options.find_files = True
        options.type_pattern = options.find_files_matching_pattern

    if options.help_types:
        print 'types'
        sys.exit(0)
    elif (len(args) == 0 and not options.find_files) or options.help:
        optparser.print_help()
        sys.exit(0)

    # Unpack args. If roots are not specified, the current directory is the
    # only root. If options.find_files is True, no pattern was specified and
    # the whole of 'args' is roots
    #
    if options.find_files:
        pattern = None
        roots = args
    else:
        pattern = args[0]
        roots = args[1:]
    if len(roots) == 0:
        roots = ['.']

    # Partition the type list to included types (--<type>) and excluded types
    # (--no<type>)
    #
    include_types = []
    exclude_types = []
    for typ in getattr(options, 'typelist', []):
        if typ.startswith('no'):
            exclude_types.append(typ[2:])
        else:
            include_types.append(typ)

    # If the context option is specified, it overrides both after-context
    # and before-context
    #
    ncontext_before = options.before_context
    ncontext_after = options.after_context
    if options.context is not None:
        ncontext_before = ncontext_after = options.context

    # Finally, invoke pss_run with the default output formatter
    # 
    pss_run(roots=roots,
            pattern=pattern,
            output_formatter=None, # use default
            only_find_files=options.find_files,
            search_all_types=options.all_types,
            search_all_files_and_dirs=options.unrestricted,
            add_ignored_dirs=options.ignored_dirs or [],
            remove_ignored_dirs=options.noignored_dirs or [],
            recurse=options.recurse,
            type_pattern=options.type_pattern,
            include_types=include_types,
            exclude_types=exclude_types,
            ignore_case=options.ignore_case,
            smart_case=options.smart_case,
            invert_match=options.invert_match,
            whole_words=options.word_regexp,
            literal_pattern=options.literal,
            max_match_count=options.max_count,
            do_colors=options.do_colors,
            prefix_filename_to_file_matches=options.prefix_filename,
            show_column_of_first_match=options.show_column,
            ncontext_before=ncontext_before,
            ncontext_after=ncontext_after)


DESCRIPTION = r'''
Search for the pattern in each source file, starting with the
current directory and its sub-directories, recursively. If
[files] are specified, only these files/directories are searched.

Only files with known extensions are searched, and this can be
configured by providing --<type> options. For example, --python
will search all Python files, and "--lisp --scheme" will search
all Lisp and all Scheme files. By default, all known file types
are searched. 

Run with --help-types for more help on how to select file types.
'''.lstrip()


def parse_cmdline(cmdline_args):
    """ Parse the list of command-line options and arguments and return a
        triple: options, args, parser -- the first two being the result of
        OptionParser.parse_args, and the third the parser object itself.`
    """
    optparser = optparse.OptionParser(
        usage='usage: %prog [options] <pattern> [files]',
        description=DESCRIPTION,
        prog='pss',
        add_help_option=False,  # -h is a real option
        version='pss %s' % __version__)

    optparser.add_option('--help-types',
        action='store_true', dest='help_types',
        help='Display supported file types')
    optparser.add_option('--help',
        action='store_true', dest='help',
        help='Display this information')

    group_searching = optparse.OptionGroup(optparser, 'Searching')
    group_searching.add_option('-i', '--ignore-case',
        action='store_true', dest='ignore_case',
        help='Ignore case distinctions in the pattern')
    group_searching.add_option('--smart-case',
        action='store_true', dest='smart_case',
        help='Ignore case distinctions in the pattern, only if the pattern '
        'contains no upper case. Ignored if -i is specified')
    group_searching.add_option('-v', '--invert-match',
        action='store_true', dest='invert_match',
        help='Invert match: show non-matching lines')
    group_searching.add_option('-w', '--word-regexp',
        action='store_true', dest='word_regexp',
        help='Force the pattern to match only whole words')
    group_searching.add_option('-Q', '--literal',
        action='store_true', dest='literal',
        help='Quote all metacharacters; the pattern is literal')
    optparser.add_option_group(group_searching)

    group_output = optparse.OptionGroup(optparser, 'Search output')
    group_output.add_option('--match', 
        action='store', dest='match', metavar='PATTERN',
        help='Specify the search pattern explicitly')
    group_output.add_option('-m', '--max-count',
        action='store', dest='max_count', metavar='NUM', default=sys.maxint,
        help='Stop searching in each file after NUM matches')
    group_output.add_option('-H', '--with-filename',
        action='store_true', dest='prefix_filename',
        help='Print the filename before matches (default)')
    group_output.add_option('-h', '--no-filename',
        action='store_false', dest='prefix_filename',
        help='Suppress printing the filename before matches')
    group_output.add_option('--column',
        action='store_true', dest='show_column',
        help='Show the column number of the first match')
    group_output.add_option('-A', '--after-context',
        action='store', dest='after_context', metavar='NUM', default=0,
        help='Print NUM lines of context after each match')
    group_output.add_option('-B', '--before-context',
        action='store', dest='before_context', metavar='NUM', default=0,
        help='Print NUM lines of context before each match')
    group_output.add_option('-C', '--context',
        action='store', dest='context', metavar='NUM',
        help='Print NUM lines of context before and after each match')
    group_output.add_option('--color',
        action='store_true', dest='do_colors',
        help='Highlight the matching text')
    group_output.add_option('--nocolor',
        action='store_false', dest='do_colors',
        help='Do not highlight the matching text')
    optparser.add_option_group(group_output)

    group_filefinding = optparse.OptionGroup(optparser, 'File finding')
    group_filefinding.add_option('-f',
        action='store_true', dest='find_files',
        help='Only print the files found. The pattern must not be specified')
    group_filefinding.add_option('-g',
        action='store', dest='find_files_matching_pattern', metavar='REGEX',
        help='Same as -f, but only print files matching REGEX')
    optparser.add_option_group(group_filefinding)

    group_inclusion = optparse.OptionGroup(optparser, 'File inclusion/exclusion')
    group_inclusion.add_option('-a', '--all-types',
        action='store_true', dest='all_types',
        help='All file types are searched')
    group_inclusion.add_option('-u', '--unrestricted',
        action='store_true', dest='unrestricted',
        help='All files are searched, including those in ignored directories')
    group_inclusion.add_option('--ignore-dir',
        action='append', dest='ignored_dirs', metavar='name',
        help='Add directory to the list of ignored dirs')
    group_inclusion.add_option('--noignore-dir',
        action='append', dest='noignored_dirs', metavar='name',
        help='Remove directory from the list of ignored dirs')
    group_inclusion.add_option('-r', '-R', '--recurse',
        action='store_true', dest='recurse', default=True,
        help='Recurse into subdirectories (default)')
    group_inclusion.add_option('-n', '--no-recurse',
        action='store_false', dest='recurse',
        help='Do not recurse into subdirectories')
    group_inclusion.add_option('-G',
        action='store', dest='type_pattern', metavar='REGEX',
        help='Only search files that match REGEX')
    optparser.add_option_group(group_inclusion)

    # Parsing --<type> and --no<type> options for all supported types is
    # done with a callback action. The callback function stores a list
    # of all type options in the typelist attribute of the options.
    #
    def type_option_callback(option, opt_str, value, parser):
        optname = opt_str.lstrip('-')
        if hasattr(parser.values, 'typelist'):
            parser.values.typelist.append(optname)
        else:
            parser.values.typelist = [optname]

    for t in TYPE_EXTENSION_MAP:
        optparser.add_option('--' + t,
            help=optparse.SUPPRESS_HELP,
            action='callback',
            callback=type_option_callback)
        optparser.add_option('--no' + t,
            help=optparse.SUPPRESS_HELP,
            action='callback',
            callback=type_option_callback)

    options, args = optparser.parse_args(cmdline_args)
    return options, args, optparser


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

