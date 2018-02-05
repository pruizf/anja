"""
Preprocesses texts so that they can be treated by anja
"""

__author__ = 'Pablo Ruiz'
__date__ = '12/08/16'
__email__ = 'pabloruizfabo@gmail.com'


import argparse
import codecs
import re


# add current dir and parent to sys.path
import inspect
import os
import sys

here = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
appbasedir = os.path.join(here, os.pardir)
sys.path.append(appbasedir)

# app specific imports
import utils as ut
import config as cfg


def BatchnamePattern(stg):
    """
    To validate cli arguments with a regex
    @note: See https://stackoverflow.com/questions/14665234
    """
    try:
        return re.match(r"^(?:xix|xv-xvii|[0-9a-z]).+", stg).group(0)
    except AttributeError:
        raise argparse.ArgumentTypeError(
            u"Batchname '{}' does not match the supported format".format(stg))


def run_argparse():
    """
    Run the argparse-based cli parser for options or defaults
    """
    # First parser collects the batch name; no help so -h collects ALL args
    # See https://gist.github.com/von/949337
    partparser = argparse.ArgumentParser(add_help=False)
    partparser.add_argument('-b', '--batch', dest='batchname',
                            type=BatchnamePattern,
                            help='String representing the name of the batch. '
                                 '(Used to name output files etc.). '
                                 'Must start with "xix" or "xv-xvii"',
                            default="xix-DUMMY")
    # Second parser collects all other argus, inheriting from first
    partargs, remaining_args = partparser.parse_known_args()
    parser = argparse.ArgumentParser(
        parents=[partparser],
        description="Preprocesses CVC poems",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    if partargs.batchname.startswith("xix"):
        parser.add_argument(
            '-i', '--input', help='Input directory', dest='inname',
            default="/home/pablo/projects/o/enca/cvc_sonnets_split/cvc_xix_split")
    elif partargs.batchname.startswith("xv"):
        parser.add_argument(
            '-i', '--input', help='Input directory', dest='inname',
            default="/home/pablo/projects/o/enca/cvc_sonnets_split/cvc_xv-xvii_split")
    else:
        parser.add_argument(
            '-i', '--input', help='Input directory', dest='inname')
    parser.add_argument('-l', '--logs', dest='logs',
                        help='Log dir, to write line-position info',
                        default=os.path.join(
                            os.path.join(cfg.baselogdir, partargs.batchname)))
    parser.add_argument('-o', '--oneline', dest='oneline',
                        help='Output dir that will contain poem on single line',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.oneline.format(batch=partargs.batchname)))
    return parser.parse_args()


def main():
    """Run"""
    argus = run_argparse()
    if argus.batchname == "xix-DUMMY":
        print "Enter a valid batch name (using the default " + \
              "'xix-DUMMY' is not allowed)"
        sys.exit(2)
    from pprint import pprint
    pprint(argus)
    for dname in [argus.oneline, argus.logs]:
        if not os.path.exists(dname):
            os.makedirs(dname)
    ti2te = ut.read_dir_into_ttl2txt_dict(argus.inname)
    ut.merge_lines_and_get_line_positions(ti2te, argus.oneline, argus.logs,
                                          argus.batchname)


if __name__ == "__main__":
    main()
