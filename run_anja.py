"""
Runs Anja with the most common options
"""

__author__ = 'Pablo Ruiz'
__date__ = '04/02/18'
__email__ = 'pabloruizfabo@gmail.com'


import argparse
import os


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
    # First parser collects the batch name and custom-sort choice;
    # no help so -h collects ALL args (see https://gist.github.com/von/949337)
    partparser = argparse.ArgumentParser(add_help=False)
    partparser.add_argument('-b', '--batch', dest='batchname',
                        help='String representing the name of the batch. '
                             '(Used to name output files etc.). ',
                        default="DEF")
    # Second parser collects all other argus, inheriting from first
    partargs, remaining_args = partparser.parse_known_args()
    parser = argparse.ArgumentParser(
        parents=[partparser],
        description="Apply enjambment detection to NLP output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input',
                        help='Input dir (contains PoS and term-id annotations',
                        dest='inname',
                        default=os.path.relpath(os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.tokwpos.format(batch=partargs.batchname))))
    parser.add_argument('-e', '--prepro',
                        help='Poem without linebreaks',
                        dest='prepro',
                        default=os.path.relpath(
                            os.path.join(cfg.sample_outdir, "prepro")))
    parser.add_argument('-l', '--logdir',
                        help='Stores line positions for each line in corpus',
                        dest='logdir',
                        default=os.path.relpath(
                            os.path.join(cfg.sample_outdir, "logs")))
    parser.add_argument('-n', '--nlpdir',
                        help='Dir containing NLP output (NAF from IXA pipes)',
                        dest='nlpdir',
                        default=os.path.relpath(os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.nlpdir.format(batch=partargs.batchname))))
    parser.add_argument('-p', '--posdir', dest='posdir',
                        help='Output dir, will contain poem with each token'
                             'annotated with a POS and term-id',
                        default=os.path.relpath(os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.tokwpos.format(batch=partargs.batchname))))
    parser.add_argument('-o', '--outdir', dest='outdir',
                        help='Output dir: poem with encabalgamiento annots',
                        default=os.path.join(
                            os.path.relpath(os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.resudir.format(batch=partargs.batchname,
                                               useconst=int(cfg.USE_CONSTITUENCY),
                                               usedep=int(cfg.USE_DEP)))))
    return parser.parse_args()


def main():
    """Run"""
    argus = run_argparse()

    # preprocessor

    precmd = "python {} -b {} -i {} -o {} -l {}".format(
        cfg.preprocessor, argus.batchname, argus.inname,
        argus.prepro, argus.logdir)
    print("- Preprocess: [{}]\n".format(precmd))
    os.popen(precmd)

    # run nlp

    nlpcmd = "{} {} {} def".format(
        cfg.nlprunner, argus.prepro, argus.nlpdir)
    print("- Run NLP: [{}]\n".format(nlpcmd))
    os.popen(nlpcmd)

    # extract pos

    #  holds positions for each line
    line_positions = os.path.join(
        argus.logdir, "{}_line_positions.txt".format(argus.batchname))

    poscmd = "python {} -b {} -i {} -o {} -p {}".format(
        cfg.posextractor, argus.batchname, argus.nlpdir, argus.posdir,
        line_positions)
    print("- Extract PoS: [{}]\n".format(poscmd))
    os.popen(poscmd)

    # detect enjambment

    #   prefix-path to a file for complete corpus results
    single_file_path = os.path.join(
        argus.outdir, cfg.single_file.format(
            batch=argus.batchname,
            useconst=int(cfg.USE_CONSTITUENCY),
            usedep=int(cfg.USE_DEP)))

    detcmd = "python {} -b {} -i {} -n {} -o {} -f {} --ruleid -5".format(
        cfg.detector, argus.batchname, argus.posdir, argus.nlpdir,
        argus.outdir, single_file_path)
    print("- Detect: [{}]".format(detcmd))
    os.popen(detcmd)


if __name__ == "__main__":
    main()