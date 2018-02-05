"""
Extract word-form, part-of-speech and term-id from terms layer of NAF results
Write out infos (term-id optional)
This version is for the zipped-file view in the Django app (poem titles are
dealt with differently than in the command-line version)
"""

__author__ = 'Pablo Ruiz'
__date__ = '16/01/16'
__email__ = 'pabloruizfabo@gmail.com'


import argparse
import codecs
from lxml.etree import XMLSyntaxError
import os
from KafNafParserPy import KafNafParser as np


# add current dir to sys.path
import inspect
import sys

here = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
sys.path.append(here)

# app specific imports
import config as cfg


def run_argparse():
    """
    Run the argparse-based cli parser for options or defaults
    """
    # First parser collects the batch name; no help so -h collects ALL args
    # See https://gist.github.com/von/949337
    partparser = argparse.ArgumentParser(add_help=False)
    partparser.add_argument('-b', '--batch', dest='batchname',
                        help='String representing the name of the batch. '
                             '(Used to name output files etc.). ',
                        default="DEF")
    # Second parser collects all other argus, inheriting from first
    partargs, remaining_args = partparser.parse_known_args()
    parser = argparse.ArgumentParser(
        parents=[partparser],
        description="Extract POS and term-id from IXA-Pipeline output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input',
                        help='Input dir (contains NAF output of IXA Pipes)',
                        dest='inname',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.nlpdir.format(batch=partargs.batchname)))
    parser.add_argument('-o', '--outdir', dest='outdir',
                        help='Output dir, will contain poem with each token'
                             'annotated with a POS and term-id',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.tokwpos.format(batch=partargs.batchname)))
    parser.add_argument('-p', '--posifile', help='File with line positions',
                        dest='posifile',
                        default=os.path.join(
                            os.path.join(cfg.baselogdir, partargs.batchname),
                            cfg.line_positions.format(batch=partargs.batchname)))
    return parser.parse_args()


def read_positions(pf):
    """
    Obtain positions for each line based on file pf
    @return: dict with positions by title and line number
    """
    pd = {}
    with codecs.open(pf, "r", "utf8") as fni:
        ll = [l.strip() for l in fni.readlines()]
        for line in ll:
            sl = line.split("\t")
            title, lnbr, posis = sl[0], int(sl[1]), sl[2].split("~")
            start, end = (int(posis[-1].split(",")[0]),
                          int(posis[-1].split(",")[1]))
            assert title and str(lnbr) and str(start) and str(end)
            pd.setdefault(title, {})
            assert lnbr not in pd[title]
            pd[title][lnbr] = start, end
    return pd


def tag_by_line(psd, pd):
    """
    Get part-of-speech info for words in a line based on parsed file psd
    and a dict with line-position info pf
    @param psd: file with part-of-speech info (NAF format)
    @param pd: dict with positions per line
    """
    print "XXXXX", os.path.splitext(os.path.basename(psd))[0]
    title = os.path.splitext(os.path.basename(psd))[0].replace("_parsed", ".txt")
    # title = os.path.splitext(os.path.basename(psd))[0].replace(".xml", ".txt")
    #title = "input.txt"
    title = title if isinstance(title, unicode) else title.decode("utf8")
    assert title in pd
    tree = np(psd)
    ln2terms = {}
    for term in tree.term_layer:
        span_ids = term.get_span().get_span_ids()
        assert len(span_ids) == 1
        wf = tree.get_token(span_ids[0])
        for lnbr, lposis in pd[title].items():
            ln2terms.setdefault(lnbr, [])
            if (int(wf.get_offset()) >= lposis[0] and int(wf.get_offset()) +
                int(len(wf.get_text())) <= lposis[1]):
                ln2terms[lnbr].append([wf.get_text(), term.get_pos(),
                                       term.get_id()])
    return ln2terms


def write_tagged_lines(tl, fno, use_tid=True):
    """
    Write out poem line by line with tag for each word in line
    @param tl: dict with pos-tagged lines, hashed by line number
    @param fno: filename for output
    @param use_tid: whether to write the term-id out or not
    """
    ols = []
    for ln, infos in sorted(tl.items()):
        if use_tid:
            ol = [cfg.TOKFMT.format(info[0], info[1], info[2])
                  for info in infos]
        else:
            ol = [cfg.TOKFMT.format(info[0], info[1])
                  for info in infos]
        ols.append(" ".join(ol))
    with codecs.open(fno, "w", "utf8") as fdo:
        fdo.write("\n".join(ols))


def run_dir(idn, odn, posis):
    """
    Apply L{tag_by_line} and L{write_tagged_lines} to each file in dir dn
    @param idn: directory name to run
    @param odn: directory name for output
    @param posis: dict with positions per line
    """
    if not os.path.exists(odn):
        os.makedirs(odn)
    for fn in sorted(os.listdir(idn)):
        #ofn = os.path.join(odn, fn.replace())
        print ur"- Annotations: {}".format(repr(fn))
        try:
            lnbr2terms = tag_by_line(os.path.join(idn, fn), posis)
        except XMLSyntaxError:
            print u"! Error with file {}".format(repr(fn))
            continue
        write_tagged_lines(lnbr2terms, os.path.join(
            odn, fn.replace(cfg.nlpsfx, cfg.possfx)))


def main():
    #cli args
    argus = run_argparse()
    # get position info
    posis = read_positions(argus.posifile)
    # recover and tag lines for all files
    run_dir(argus.inname, argus.outdir, posis)


if __name__ == "__main__":
    main()
