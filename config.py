"""Config for enca2 batches"""

__author__ = 'Pablo Ruiz'
__date__ = '09/08/16'
__email__ = 'pabloruizfabo@gmail.com'

import re


# set basedir to dir containing this module
import inspect
import os


basedir = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
parentdir = os.path.join(basedir, os.pardir)


# General options =============================================================

USE_CONSTITUENCY = False  # use it in enca detection
USE_DEP = True            # use dependencies in enca detection
WRITE_TID = True          # write out term-id in extract_pos_and_tid
NORM_ETAGS = True         # normalize enjambment type tags based on
                          # file given at entagnorm below
PRINT_RULEIDS = True     # write rule-ids to output
MORE14 = False           # allow tagging more than 14 lines (extends to 17 for estrambote)
LOG = False               #

#IO: paths are directory basenames ============================================

baselogdir = os.path.join(parentdir, "enca2texts" + os.sep + "enca2logs")
baseoutdir = os.path.join(parentdir, "enca2texts" + os.sep + "enca2out")
datadir = os.path.join(basedir, "data")
# config how to manage tags
tag_confdir = os.path.join(basedir, "config_tags")
# for the IO tests
sample_outdir = os.path.join(datadir, "sample" + os.sep + "out")
for dn in baselogdir, baseoutdir, datadir, sample_outdir:
    if not os.path.exists(dn):
        os.makedirs(dn)


# I: poem on split lines, O: poem on one line ----------------------------
splitdir = u"{batch}_split"
oneline = u"{batch}_oneline"
# line positions
line_positions = u"{batch}_line_positions.txt"


# I: NAF (consts and optionally dep+srl), O: token-pos tuples ------------
if USE_DEP:
    nlpdir = u"{batch}_parsed"
else:
    nlpdir = u"{batch}_parsed_nodeps"
if WRITE_TID:
    TOKFMT = u"{{{} {} {}}}"
    tokwpos = u"{batch}_postid"
else:
    tokwpos = u"{batch}_pos"
    TOKFMT = u"{{{} {}}}"
nlpsfx = "_parsed.xml"    # suffix for files coming out of nlp pipeline
possfx = "_annot.txt"     # suffix for files annotated with pos (and term-id)


# I: token-pos tuples, O: token-pos tuples tagged for enca ---------------
# I2: NAF (consts and optionally dep+srl). Needed for syntactic info

resudir = u"{batch}_results_const_{useconst}_deps_{usedep}"
single_file = u"{batch}_corpus_results_const_{useconst}_deps_{usedep}.txt"

# filename template for list with custom output sort order (optional)
output_sorter = u"{batch}_sorter.txt"

# splits line format in "../annot" into (word-form, pos, term-id) elements
TOKRE = re.compile(ur"{([^ ]+) ([^}]+) ([^}]+)}")

# Scripts config ==============================================================
scriptdir = os.path.join(basedir, "scripts")
scriptdatadir = os.path.join(scriptdir, "data")

nlprunner = os.path.join(basedir, "run_nlp.sh")
preprocessor = os.path.join(basedir, os.path.join("prepro", "prepro.py"))
posextractor = os.path.join(basedir, "extract_pos.py")
detector = os.path.join(basedir, "detect.py")

# Enjambment tagging config ===================================================
entagnorm = os.path.join(tag_confdir, "enca_tags_normalization.txt")

# Resources ===================================================================
lexdata = os.path.join(datadir, "lexical")
# dicts
suplemento = os.path.join(lexdata, "suplemento.txt")
periphrases = os.path.join(lexdata, "periphrases.txt")
tag_translation = os.path.join(tag_confdir, "enca_tags_translation.txt")

# Logging =======================================================================

log_filename = u"{batch}_log.txt"

