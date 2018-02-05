# coding: utf-8

"""
Detect some types of encabalgamiento given pos-tags and constituency at
line boundaries, as well as syntactic dependencies (from IXA Pipes results).
Writes out in several formats, including a tsv format evaluable with
the neleval tool (github.com/wikilinks/neleval)
Assumes KafNafParserPy (github.com/cltl/KafNafParserPy) at an importable path.
"""

__author__ = 'Pablo Ruiz'
__date__ = '16/01/16'
__email__ = 'pabloruizfabo@gmail.com'


import argparse
import codecs
import os
import re
from string import punctuation

import KafNafParserPy as knp
from KafNafParserPy import KafNafParser as np

# add current dir
import inspect
import sys

here = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
sys.path.append(here)

# app specific imports
import config as cfg
import utils as ut


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
    partparser.add_argument('-t', '--customsort', dest='customsort',
                            action='store_true',
                            help='ask for a list to sort output files by')
    partparser.add_argument('-r', '--restrictfiles', dest='restrictfiles',
                            action='store_true',
                            help='restrict to filenames in the list')
    # Second parser collects all other argus, inheriting from first
    partargs, remaining_args = partparser.parse_known_args()
    parser = argparse.ArgumentParser(
        parents=[partparser],
        description="Apply enjambment detection to NLP output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input',
                        help='Input dir (contains PoS and term-id annotations',
                        dest='inname',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.tokwpos.format(batch=partargs.batchname)))
    parser.add_argument('-c', '--constituency', action='store_true',
                        help='Use constituency info from NLP output')
    parser.add_argument('-d', '--dependency', action='store_true',
                        help='Use dependency info from NLP output')
    parser.add_argument('-n', '--nlpdir',
                        help='Dir containing NLP output (NAF from IXA pipes)',
                        dest='nlpdir',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.nlpdir.format(batch=partargs.batchname)))
    parser.add_argument('-l', '--lang', dest='lang', default='en',
                        help='Language for enjambment tags (English or Spanish)')
    parser.add_argument('-o', '--outdir', dest='outdir',
                        help='Output dir: poem with encabalgamiento annots',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.resudir.format(batch=partargs.batchname,
                                               useconst=int(cfg.USE_CONSTITUENCY),
                                               usedep=int(cfg.USE_DEP))))
    parser.add_argument('-f', '--singlefile',
                        help='Name for single file that will hold results'
                             ' for complete corpus',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.single_file.format(
                                batch=partargs.batchname,
                                useconst=int(cfg.USE_CONSTITUENCY),
                                usedep=int(cfg.USE_DEP))))
    parser.add_argument('-e', '--logdetails',
                        help='Log rule application details for rules where defined',
                        action='store_true')
    parser.add_argument('-g', '--logfile', help='Path to log',
                        default=os.path.join(
                            os.path.join(cfg.baseoutdir, partargs.batchname),
                            cfg.log_filename.format(batch=partargs.batchname)))
    parser.add_argument('-u', '--ruleid',
                        help='Print out rule ids',
                        action='store_true')
    parser.add_argument('-5', '--m14',
                        help='Allow rule application above 14 lines',
                        action='store_true')
    if 'customsort' in partargs and partargs.customsort:
        parser.add_argument('-s', '--sorter',
                            help='File for custom result sort order',
                            dest='sorter',
                            default=os.path.join(
                                os.path.join(cfg.datadir,
                                cfg.output_sorter.format(
                                    batch=partargs.batchname))))
    if 'restrictfiles' in partargs and partargs.restrictfiles:
        parser.add_argument('-k', '--keepfilelist', dest='keepfilelist')
    parser.set_defaults(customsort=False, constituency=cfg.USE_CONSTITUENCY,
                        dependency=cfg.USE_DEP, ruleid=cfg.PRINT_RULEIDS,
                        m14=cfg.MORE14)
    return parser.parse_args()


# relevant for some rules
PRON_ATONO = ["me", "te", "se", "nos", "os", "vos"]
ACC = [u"á", u"é", u"í", u"ó", u"ú"]
PREPS = ["a", "al", "ante", "bajo", "con", "contra", "desde", "en", "entre", 
         "hacia", "hasta", "para", "por", "según", "sin", "sobre", "tras",
         "mediante", "durante", "salvo", "excepto", "cabe", "so"]
# to have uniform labels on enca output
REPS = {"N": "noun", "G": "adj", "A": "adv", "D": "det", "O": "other",
        "V": "verb", "Q": "cuantif", "R": "propn"}


def detect(fn, lf, tokp, naffn, lxinfo, lang, useconst, usedep, m14):
    """
    Apply encabalgamiento rules to part-of-speech tagged lines, with access
    to dependencies and constituents in a NAF file via term-id.
    Lines are lists of format[(word-form_1, pos-tag_1, term-id_1), ...,
    (wf_n, pos-tag_n, term-id_n)]
    @param fn: filename for the poem (used to long info per file)
    @param lf: log filehandle open to write
    @param tokp: list of tokens as described
    @param naffn: need this to create a NAF tree (for constituents)
    @param lxinfo: dict of dicts with lexical info like verbs governing
    'suplemento' prepositional complement etc.
    @param lang: language for enjambment tags (en (default) or es)
    @param useconst: use constituency info or not (bool)
    @type useconst: bool
    @param usedep: use dependency info or not (bool)
    @type usedep: bool
    @param m14: allow rule application beyond 14 lines (actually extends to 1
    for estrambote, so it's actually beyond 17 lines)
    """
    detections = {}
    keeps = {}
    dones = set()
    naffn = naffn.replace(".txt", ".xml")
    tree = np(naffn)
    extractor = knp.feature_extractor.constituency.Cconstituency_extractor(tree)
    try:
        deps = list(tree.get_dependencies())
    except TypeError:
        print "No dep layer for file: {}".format(naffn)
        usedep = False
    for idx, toklist in enumerate(tokp):
        has_enca = False
        if idx < len(tokp) - 1:
            cline = toklist
            nline = tokp[idx+1]
        else:
            cline = tokp[idx-1]
            nline = toklist
        # variable names mean:
        #   wf: word-form, pos: pos, tid: term-id
        ctids = [tok[2] for tok in cline]
        ntids = [tok[2] for tok in nline]
        try:
            cwf, cpos, ctid = cline[-1][0], cline[-1][1], cline[-1][2]    # last
            nwf, npos, ntid = nline[0][0], nline[0][1], nline[0][2]       # first
        except IndexError:
            cwf, cpos, ctid = "", "", ""
            nwf, npos, ntid = "", "", ""
        # lemmas
        try:
            clemma = [te.get_lemma() for te in tree.term_layer
                      if te.get_id() == ctid][0]
            # nlemma = [te.get_lemma() for te in tree.term_layer
            #           if te.get_id() == ntid][0]
        except IndexError:
            clemma = ""
        clemmas = [te.get_lemma() for te in tree.term_layer
                   if te.get_id() in ctids]
        # check if any lemma in cline is verb which can take 'suplemento' complement
        suplemento_lemma = [lem for lem in clemmas if lem in lxinfo["suplemento"]]
        # will need to use the penult and second in some cases
        # for higher indexes i'm just accessing nline[idx > 1] directly
        try:
            pwf, ppos, ptid = cline[-2][0], cline[-2][1], cline[-2][2]            # penult
            swf, spos, stid = nline[1][0], nline[1][1], nline[1][2]               # second
        except IndexError:
            print ur"Line has less than two tokens: {}".format(cline)
            pwf, ppos, ptid = "", "", ""
            swf, spos, stid = "", "", ""
        # RULES USING WORD-FORM ONLY ==========================================
        # tmesis (no se da en _Noche_)
        #   note: tokenizer errors with ".-" (different in each tok version)
        if len(cwf) > 1 and cwf[-1] == "-" and cwf != ".-":
            ut.update_span(detections, idx, "tmesis", "t001", dones, m14)
            has_enca = True
        # RULES WITHOUT SYNTAX ================================================
        # noun + adjective // + noun
        elif tuple(sorted((ppos, cpos, npos))) == ("G", "N", "N"):
            ut.update_span(detections, idx, "sirrem_adj_noun", "pp01", dones, m14)
            has_enca = True
        # noun + adjective ----------------------------------------------------
        elif tuple(sorted((cpos, npos))) == ("G", "N"):
            ut.update_span(detections, idx, "sirrem_adj_noun", "pp02", dones, m14)
            has_enca = True
        # noun // + adv + adjective (e.g. monumento nunca oprimido)
        elif True and tuple(sorted((cpos, npos, spos))) == ("A", "G", "N"):
            ut.update_span(detections, idx, "sirrem_adj_noun", "pp03", dones, m14)
            has_enca = True
        # adj // + noun + adj with misanalysis of adj/participle as adv
        # (e.g. apasionada corona liberal)
        elif (True and tuple(sorted((cpos, npos, spos))) == ("A", "G", "N") and
              cwf.endswith("ada")):
            ut.update_span(detections, idx, "sirrem_adj_noun", "pp04", dones, m14)
            has_enca = True
        # noun + adj // + prep-de ---------------------------------------------
        elif (tuple(sorted((ppos, cpos, npos))) == ("G", "N", "P") and
              nwf.lower() in ("de", "del")):
            ut.update_span(detections, idx, "sirrem_noun_prep-de", "pp05", dones, m14)
            has_enca = True
        # noun + prep ---------------------------------------------------------
        elif (ppos, cpos, npos) == ("N", "P", "D") and cwf.lower() in ("de", "del"):
            ut.update_span(detections, idx, "sirrem_noun_prep-de", "pp06", dones, m14)
            has_enca = True
        elif (cpos, npos) == ("N", "P") and nwf.lower() in ("de", "del"):
            ut.update_span(detections, idx, "sirrem_noun_prep-de", "pp06.1", dones, m14)
            has_enca = True
        # adj + prep-de -------------------------------------------------------
        elif (cpos, npos) == ("G", "P") and nwf.lower() in ("de", "del"):
            ut.update_span(detections, idx, "sirrem_adj_prep-de", "pp07", dones, m14)
            has_enca = True
        # adj + adv -----------------------------------------------------------
        elif False and tuple(sorted((cpos, npos))) == ("A", "G"):       # overapplies
            ut.update_span(detections, idx, "sirrem_adj_adv", "pp08", dones, m14)
            has_enca = True
        # work around pos errors (participles tagged as A)
        elif (cpos, npos) == ("A", "G") and not re.search(r"[ai]d[oa]s?$", cwf):
            ut.update_span(detections, idx, "sirrem_adj_adv", "pp09", dones, m14)
            has_enca = True
        #avoid errors like 'azul dentro de' being tagged as enjambment
        elif ((cpos, npos) == ("G", "A") and swf not in ("de", "del") and not
                re.search(r"[ai]d[oa]s?$", nwf)):
            ut.update_span(detections, idx, "sirrem_adj_adv", "pp10", dones, m14)
            has_enca = True

        # verb + adverb -------------------------------------------------------
        elif tuple(sorted((cpos, npos))) == ("A", "V"):
            ut.update_span(detections, idx, "sirrem_verb_adv", "pp11", dones, m14)
            has_enca = True
        # palabra de relación -------------------------------------------------
        #   pron átonos ---------------
        elif cpos == "Q" and cwf.lower() in PRON_ATONO:
            ut.update_span(detections, idx, "sirrem_pal-rel~clitic", "pp12", dones, m14)
            has_enca = True
        # adverbial clause
        elif ppos == "O" and cwf.lower() in ("cuando", "donde") and npos == "V":
            ut.update_span(detections, idx, "sirrem_pal-rel~conj", "pp13", dones, m14)
            has_enca = True

        #   conjunción ----------------
        elif cpos == "C":
            ut.update_span(detections, idx, "sirrem_pal-rel~conj", "pp14", dones, m14)
            has_enca = True
        #   preposition ---------------
        elif cpos == "P":
            if cwf in PREPS:
                ut.update_span(detections, idx, "sirrem_pal-rel~prep", "pp15", dones, m14)
                has_enca = True
        #   determiners ---------------
        #   (needs to precede noun, adj, adverb, determiner)
        elif cpos == "D" and npos in ("N", "G", "A", "D"):
            ut.update_span(detections, idx, "sirrem_pal-rel~det", "pp16", dones, m14)
            has_enca = True
        # verb + verb (perífrasis verbal o tiempo compuesto etc.) -------------
        elif False and (cpos, npos) == ("V", "V"):              # overapplies
            ut.update_span(detections, idx, "sirrem_perif_verb", "pp17", dones, m14)
            has_enca = True
        # verb + prep + verb (perífrasis verbal)
        elif False and (cpos, npos, spos) == ("V", "P", "V"):   # overapplies
            ut.update_span(detections, idx, "sirrem_perif_verb", "pp18", dones, m14)
            has_enca = True
        # new periphrasis rules (dictionary-based)
        #   [verb // prep + verb] or [verb // prep + clitic + verb]
        elif (clemma in lxinfo["periphrases"] and
              nwf in lxinfo["periphrases"][clemma]["ponly"] and
              # [// prep + V] or [// prep + preposed clitic + V (archaic)]
              (spos == "V" or (spos == "Q" and nline[2][1] == "V"))):
            ut.update_span(detections, idx, "sirrem_perif_verb", "pp19", dones, m14)
            has_enca = True
        #   [verb // verb|participle] ("G" possible participle for pos-errors)
        elif (clemma in lxinfo["periphrases"] and not
              lxinfo["periphrases"][clemma]["ponly"] and
              ((npos == "V") or ("G" in lxinfo["periphrases"][clemma]["tonly"]
                                 and npos == "G"))):
            ut.update_span(detections, idx, "sirrem_perif_verb", "pp20", dones, m14)
            has_enca = True
        # [verb // verb], general rule for any aux verb in list
        elif (clemma in lxinfo["periphrases"] and
              lxinfo["periphrases"][clemma]["tonly"] and
              npos == "V"):
            ut.update_span(detections, idx, "sirrem_perif_verb", "pp21", dones, m14)
            has_enca = True

        # verbo + suplemento --------------------------------------------------
        # aproximación [verbo + prep_de] overapplies
        elif False and (cpos, npos) == ("V", "P") and nwf.lower() in ("de", "del"):
            ut.update_span(detections, idx, "sirrem_verb_supl", "pp22", dones, m14)
            has_enca = True
        # (aproximación: verbo + prep if verb lemma and prep in
        #  a configurable list in lxinfo)
        elif (cpos, npos) == ("V", "P") and (clemma in lxinfo["suplemento"] and
                nwf in lxinfo["suplemento"][clemma]):
            ut.update_span(detections, idx, "sirrem_verb_supl", "pp23", dones, m14)
            has_enca = True
        elif (cpos, npos) == ("G", "P") and (clemma in lxinfo["suplemento"] and
                nwf in lxinfo["suplemento"][clemma]):
            ut.update_span(detections, idx, "sirrem_verb_supl", "pp24", dones, m14)
            has_enca = True
        elif (clemma in lxinfo["suplemento"] and
                nwf in lxinfo["suplemento"][clemma]):
            ut.update_span(detections, idx, "sirrem_verb_supl", "pp25", dones, m14)
            has_enca = True
        elif (len(suplemento_lemma) > 0 and nwf.lower()
              in lxinfo["suplemento"][suplemento_lemma[0]]):
            ut.update_span(detections, idx, "sirrem_verb_supl", "pp26", dones, m14)
            has_enca = True

        # oracional -----------------------------------------------------------
        elif (cpos in ("G", "N", "Q", "R") and npos == "Q"
              and nwf.lower() in ("que", "cuyo", "cuya", "cuyos",
                                  "cuyas", "donde")):
                                  # 'adonde' many errors in xv-xvii
            etypes = {"comp-noun": ["G", "N", "R"], "comp-pron": ["Q"]}
            etype = [ke for ke, va in etypes.items() if cpos in va][0]
            ut.update_span(detections, idx, "oracional_{}".format(etype), "cp01", dones, m14)
            has_enca = True
        #   adverbial clause (a quien, con quien ...)
        elif False and (cpos in ("G", "N", "Q", "R") and spos == "Q"
              and npos == "P"
              and swf.lower() in ("que", "cuyo", "cuya", "cuyos",
                                  "cuyas", "donde")):
                                  # 'adonde' many errors in xv-xvii
            etypes = {"comp-noun": ["G", "N", "R"], "comp-pron": ["Q"]}
            etype = [ke for ke, va in etypes.items() if cpos in va][0]
            ut.update_span(detections, idx, "oracional_{}".format(etype), "cp02", dones, m14)
            has_enca = True

        # RULES THAT NEED CONSTITUENCY INFO ====================================
        # complemento del nombre (noun seguido de prep (salvo 'de')
        # en mismo constituyente)
        elif useconst and tuple((cpos, npos)) == ("N", "P"):
            for chunk_type, tid_list in extractor.get_all_chunks_for_term(
                    ctid):
                if (chunk_type == "GRUP.NOM" and ntid in tid_list
                    and nwf not in ("de", "del")):
                    ut.update_span(detections, idx,
                                   "sirrem_noun_prep-{}".format(nwf), "pc01",
                                   dones, m14)
                    has_enca = True
        # complemento del adjetivo (adj seguido de prep (salvo 'de')
        # en mismo constituyente)
        elif useconst and tuple((cpos, npos)) == ("G", "P"):
            for chunk_type, tid_list in extractor.get_all_chunks_for_term(
                    ctid):
                if (chunk_type == "GRUP.A" and ntid in tid_list
                    and nwf not in ("de", "del")):
                    ut.update_span(detections, idx,
                                   "sirrem_adj_prep-{}".format(nwf), "pc02",
                                   dones, m14)
                    has_enca = True
        # RULES USING DEPS ====================================================
        #TODO keepdep thing is repetitive, refactor
        # análisis como agente de pasiva (puede haber errores)
        elif usedep and [hd for hd in deps if hd.get_function() == "cag"
              and hd.get_from() == ctid]:
            ut.update_span(detections, idx,
                           u"sirrem_{}_prep-{}".format(REPS[cpos], nwf),
                           "pd01", dones, m14)
            has_enca = True
            # logging
            keepdep = [hd for hd in deps if hd.get_function() == "cag"
                       and hd.get_from() == ctid]
            cfg.LOG or lf is not None and ut.logdep(
                fn, tree, lf, idx, "pd01", (cwf, cpos, ctid), (nwf, npos, ntid),
                (pwf, ppos, ptid), (swf, spos, stid), keepdep[0])
        # complementos preposicionales de n/adj no introducidos por 'de(l)'
        # n/adj precede a prep
        elif usedep and [hd for hd in deps if hd.get_function() == "sp"
                and hd.get_to() == ntid and nwf.lower() not in ("de", "del")
                # remove restriction on nwf to repro errors when REPS had N G only
                and nwf.lower() in PREPS
                and hd.get_from() in (ctid, ptid) and cpos in ("N", "G")]:
            ut.update_span(detections, idx,
                           u"sirrem_{}_prep-{}".format(REPS[cpos],
                           nwf.lower()), "pd02", dones, m14)
            has_enca = True
            # logging
            keepdep = [hd for hd in deps if hd.get_function() == "sp"
                and hd.get_to() == ntid and nwf.lower() not in ("de", "del")
                # remove restriction on nwf to repro errors when REPS had N G only
                and nwf.lower() in PREPS
                and hd.get_from() in (ctid, ptid) and cpos in ("N", "G")][0]
            cfg.LOG or lf is not None and ut.logdep(
                fn, tree, lf, idx, "pd02", (cwf, cpos, ctid), (nwf, npos, ntid),
                (pwf, ppos, ptid), (swf, spos, stid), keepdep)
        # prep precede a n/adj
        elif usedep and [hd for hd in deps if hd.get_function() == "sn"
              and hd.get_to() == ntid and cwf not in ("de", "del") and pwf.lower()
              not in ("de", "del")
              and hd.get_from() in (ctid, ptid) and "P" in (cpos, ppos)]:
            if ((cpos == "P" and cwf in PREPS and npos in ("G", "N")) or
                    (ppos == "P" and pwf in PREPS and npos in ("G", "N"))):
                wfo = cwf.lower() if cpos == "P" else pwf.lower()
                ut.update_span(detections, idx,
                               u"sirrem_{}_prep-{}".format(REPS[npos], wfo),
                               "pd03", dones, m14)
                has_enca = True
                # logging
                keepdep = [hd for hd in deps if hd.get_function() == "sn"
                           and hd.get_to() == ntid and cwf not in ("de", "del")
                           and pwf.lower() not in ("de", "del")
                           and hd.get_from() in (ctid, ptid) and "P" in (cpos, ppos)]
                cfg.LOG or lf is not None and ut.logdep(
                    fn, tree, lf, idx, "pd03", (cwf, cpos, ctid), (nwf, npos, ntid),
                    (pwf, ppos, ptid), (swf, spos, stid), keepdep[0])
        # enlaces -----------------------------------------
        elif usedep:
            if [hd for hd in deps if hd.get_function() == "suj" and
                  cwf not in punctuation and (
                  (hd.get_from() in ctids and hd.get_to() in ntids) or
                  (hd.get_to() in ctids and hd.get_from() in ntids))]:
                ut.update_span(detections, idx, u"enlace_subj_verb", "ld01", dones, m14)
                has_enca = True
                # logging
                keepdep = [hd for hd in deps if hd.get_function() == "suj" and
                           cwf not in punctuation and (
                           (hd.get_from() in ctids and hd.get_to() in ntids) or
                           (hd.get_to() in ctids and hd.get_from() in ntids))]
                cfg.LOG or lf is not None and ut.logdep(
                    fn, tree, lf, idx, "ld01", (cwf, cpos, ctid), (nwf, npos, ntid),
                    (pwf, ppos, ptid), (swf, spos, stid), keepdep[0])
            elif [hd for hd in deps if hd.get_function() == "cd"
                  and cwf not in punctuation and (
                  (hd.get_from() in ctids and hd.get_to() in ntids) or
                  (hd.get_to() in ctids and hd.get_from() in ntids))]:
                ut.update_span(detections, idx, u"enlace_od_verb", "ld02", dones, m14)
                has_enca = True
                # logging
                keepdep = [hd for hd in deps if hd.get_function() == "cd"
                           and cwf not in punctuation and (
                           (hd.get_from() in ctids and hd.get_to() in ntids) or
                           (hd.get_to() in ctids and hd.get_from() in ntids))]
                cfg.LOG or lf is not None and ut.logdep(
                    fn, tree, lf, idx, "ld02", (cwf, cpos, ctid), (nwf, npos, ntid),
                    (pwf, ppos, ptid), (swf, spos, stid), keepdep[0])

        # RULES END ===========================================================
        # postprocess bad tokenization cases
        #     deal with wrongly added annotations
        if cwf and cwf[-1] in punctuation:
            has_enca = False
            try:
                filt = [tu for tu in detections[idx] if tu[0] != "B"]
                detections[idx] = filt
                filt1 = [tu for tu in detections[idx+1] if tu[0] != "I"]
                detections[idx+1] = filt1
            except KeyError:
                pass
        # add to hash with enca lines
        if has_enca:
            keeps[idx] = True
            keeps[idx + 1] = True
        # line is not part of encabalgamiento
        else:
            if idx not in keeps:
                detections.setdefault(idx, [])
                if len(detections[idx]) == 0:
                    detections[idx].append(("O", "", "00"))
            if idx+1 not in keeps:
                detections.setdefault(idx+1, [])
                if len(detections[idx+1]) == 0:
                    detections[idx+1].append(("O", "", "00"))

        # enjambment tag normalization (to use broad vs detailed tags)
        if cfg.NORM_ETAGS:
            normtags = [(annot[0], ut.normalize_enca_types(cfg, annot[1]), annot[2])
                        for annot in detections[idx]]
            detections[idx] = normtags
            normtags1 = [(annot[0], ut.normalize_enca_types(cfg, annot[1]), annot[2])
                         for annot in detections[idx+1]]
            detections[idx+1] = normtags1
        # translate enjambment tag to Spanish if needed
        if lang == "es":
            transtags = [(annot[0], ut.translate_enca_tag(cfg, annot[1]), annot[2])
                         for annot in detections[idx]]
            detections[idx] = transtags
            transtags1 = [(annot[0], ut.translate_enca_tag(cfg, annot[1]), annot[2])
                          for annot in detections[idx+1]]
            detections[idx+1] = transtags1
    return detections


def write_out(toks, res, ofn, tsv=False, rids=False):
    """
    Writes out poems annotated for encabalgamiento and its type,
    one file per poem.
    Merges each line token list (toks) with the annotation for that line (res)
    @param toks: poem lines as lists of tokens
    @param res: lists of lines with encabalgamiento annotation
    @param ofn: name of output file
    @param tsv: if True, formats output so that looks nicer on a spreadsheet
    """
    ols = []
    for idx, al in enumerate(toks):
        # write out each token as {word-for, pos-tag}
        otoks = " ".join([u"{{{} {}}}".format(info[0], info[1])
                          for info in al])
        # gather the infos
        #   no 'B' allowed in last line: filter out
        if idx == len(toks) - 1:
            btags = []
        else:
            btags = [it for it in res[idx] if it[0] == "B"]
        itags = [it for it in res[idx] if it[0] == "I"]
        otags = [it for it in res[idx] if it[0] == "O"]
        posis = "".join([i[0] for i in itags] + [b[0] for b in btags] +
                         [o[0] for o in otags])
        if tsv:
            typetags = '"' + "\n".join([i[1] for i in itags] + \
                                       [b[1] for b in btags]) + '"'
            if rids:
                ruleids = '"' + "\n".join([i[2] for i in itags] + \
                                          [b[2] for b in btags]) + '"'
        else:
            typetags = ";".join([i[1] for i in itags] + [b[1] for b in btags])
            if rids:
                ruleids = ";".join([i[2] for i in itags] + [b[2] for b in btags])
        oinfos = [otoks, posis, typetags]
        if rids:
            oinfos.append(ruleids)
        # out
        ol = "\t".join(tuple(oinfos))
        ols.append(ol)
    with codecs.open(ofn, "w", "utf8") as ofd:
        ofd.write("\n".join(ols))


def write_out_to_single_file(toks, res, title, ofn, write_header=False,
                             tsv=False, rids=False):
    """
    Writes out poems annotated for encabalgamiento and its type to a single file
    (can use to open with spreadsheet)
    Merges each line token list (toks) with the annotation for that line (res)
    @param toks: poem lines as lists of tokens
    @param res: lists of lines with encabalgamiento annotation
    @param title: each file-name in corpus (to get title for the poem)
    @param ofn: name of output file
    @param tsv: if True, formats output so that looks nicer on a spreadsheet
    @param write_header: to add a header on first writing to the results file
    """
    if write_header:
        ols = [u"title\tlnbr\tline\tenca_position\tenca_type"]
        if rids:
            ols[0] += "\trule_ids"
    else:
        ols = []
    #clean_fn = re.sub("_.+", "", os.path.splitext(os.path.basename(title))[0])
    clean_fn = os.path.splitext(os.path.basename(title))[0]
    for idx, al in enumerate(toks):
        otoks = " ".join([u"{{{} {}}}".format(info[0], info[1])
                          for info in al])
        # collect the infos
        #   no 'B' allowed in last line: filter out
        if idx == len(toks) - 1:
            btags = []
        else:
            btags = [it for it in res[idx] if it[0] == "B"]
        itags = [it for it in res[idx] if it[0] == "I"]
        otags = [it for it in res[idx] if it[0] == "O"]
        posis = "".join([i[0] for i in itags] + [b[0] for b in btags] +
                        [o[0] for o in otags])
        if tsv:
            # otags no influence if btags or itags filled, else adds empty col
            typetags = '"' + "\n".join([i[1] for i in itags] + \
                                       [b[1] for b in btags] + \
                                       [o[1] for o in otags]) + '"'
            if rids:
                ruleids = '"' + "\n".join([i[2] for i in itags] + \
                                          [b[2] for b in btags]) + '"'
        else:
            typetags = ";".join([i[1] for i in itags] + [b[1] for b in btags])
            if rids:
                ruleids = ";".join([i[2] for i in itags] + [b[2] for b in btags] +
                                   [o[2] for o in otags])
        # out
        if isinstance(clean_fn, str):
            clean_fn_fmt = clean_fn.decode("utf8")
        else:
            clean_fn_fmt = clean_fn
        oinfos = [clean_fn_fmt, str(idx + 1), otoks, posis, typetags]
        if rids:
            oinfos.append(ruleids)
        ol = "\t".join(tuple(oinfos))
        ols.append(ol)
    with codecs.open(ofn, "a", "utf8") as ofd:
        ofd.write("\n".join(ols))
        ofd.write("\n")


def write_standoff(di, fn, of, rids=False):
    """
    Write standoff annotations in neleval format (github.com/wikilinks/neleval)
    Format is Title\tLineNbr1\LineNbr2\ttype\tDummyNr\ttype.
    Using both the link column (4) and type column (last) to write the type,
    that way can better evaluate type errors with ./nel analyze
    @param di: dict with encabalgamiento infos
    @param fn: input file name
    @param of: output file name
    """
    outs = []
    # skip last (superfluous)
    sinfos = sorted(di.items()[0:-1])
    for idx, (ke, infos) in enumerate(sinfos):
        try:
            assert ke + 1 == sinfos[idx+1][0]
        except IndexError:
            pass
        try:
            for posi, ttype, rid in infos:
                for posi2, ttype2, rid2 in sinfos[idx+1][1]:
                    if (posi, posi2) == ("B", "I") and ttype == ttype2:
                        oinfos = [fn.replace("_annot.txt", ""),
                                  ke+1, ke+2, ttype, 1, ttype]
                        if rids:
                            assert rid == rid2
                            oinfos.append(rid)
                        outs.append(tuple(oinfos))
        except IndexError:
            pass
    with codecs.open(of, "a", "utf8") as outf:
        for ol in outs:
            #outf.write("\t".join([unicode(it) for it in ol]))
            outf.write("\t".join([it.decode("utf8") if isinstance(it, str)
                                  else it.encode("utf8").decode("utf8") if isinstance(it, unicode)
                                  else str(it)
                                  for it in ol]))
            outf.write("\n")


def run_dir(idn, odn, single_f, nafdir, lang, useconst, usedep, m14=cfg.MORE14,
            logfn=None, sorter_list_fn=None, restrict_to_list_fn=None,
            print_rule_ids=None):
    """
    Runs other functions in the module
    @param idn: dir with poems annotated w pos and term-id
    @param odn: output dir
    @param single_f: path for single path output
    @param nafdir: naf annotations are in this dir (used for constituents
    and dependencies)
    @param useconst: use constituency or not
    @type useconst: bool
    @param usedep: use dependency or not
    @type useconst: bool
    @param rs14: restrict rule application to 14 lines or not
    @param sorter_list_fn: path to file with custom sorting order
    @param restrict_to_list_fn: path to file with list of poems to analyze
    (use this to filter a larger directory, analyzing those files only)
    @param print_rule_ids: will add column with rule ids to results, with
    L{cfg.PRINT_RULEIDS} as default
    @type print_rule_ids: bool
    """
    ## debug
    global lexinfo
    ##
    if not os.path.exists(odn):
        os.makedirs(odn)
    # remove previous versions of files in append mode
    if os.path.exists(single_f):
        os.remove(single_f)
    # paths to tsv and sto
    tsvfile = re.sub("\.txt$", ".tsv", single_f)
    standoff = re.sub("\.txt$", "_sto.txt", single_f)
    norules = re.sub("_sto.txt", "_sto_norules.txt", standoff)
    if os.path.exists(standoff):
        os.remove(standoff)
    if os.path.exists(tsvfile):
        os.remove(tsvfile)
    # output sorting
    if sorter_list_fn is not None:
        # custom (files to skip will move to end, they start with '__')
        sorter_list = ut.file_to_ordered_list(sorter_list_fn)
        sorted_outfile_list = sorted(
            os.listdir(idn), key=lambda finame: sorter_list.index(
            re.sub("_.*", "", finame)))
    else:
        # standard
        sorted_outfile_list = sorted(os.listdir(idn))
    # check filenames to analyze
    if restrict_to_list_fn is not None:
        keeplist = ut.read_filenames_to_restrict_detection(restrict_to_list_fn)
    else:
        keeplist = sorted_outfile_list
    # open log
    if logfn is not None:
        logfh = codecs.open(logfn, "w", "utf8")
    else:
        logfh = None
    # load lexical infos
    lexinfo = dict()
    lexinfo["suplemento"] = ut.read_suplemento(cfg)
    lexinfo["periphrases"] = ut.read_periphrases(cfg)
    # process
    dones = 0
    print u"- Allow rule application beyond 17 lines (0=n 1=y): [{}]".format(
        int(m14))
    # for fn in sorted_outfile_list:
    for fn in keeplist:
        if isinstance(fn, str):
            fnfmt = fn.decode("utf8")
        else:
            fnfmt = fn
        if fn.startswith("__"):
            print u"! Skipping (manually) [{}]".format(fnfmt)
            continue
        #print ur"- Detect: {}".format(fn)
        print ur"- Detect: {}".format(repr(fnfmt))
        ffn = os.path.join(idn, fn)
        naffn = os.path.join(nafdir, fn.replace("_annot.txt", "_parsed.xml"))
        ofn = os.path.join(odn, fn.replace("_annot.txt", "_results.txt"))
        # processing
        toks = ut.read_pos_tagged_poem(ffn)
        ana = detect(fn, logfh, toks, naffn, lexinfo, lang, useconst, usedep, m14)
        # write to individual files per poem
        write_out(toks, ana, ofn, rids=print_rule_ids)
        # write all to a single file (to open in spreadsheet, tsv reads nicer)
        if dones == 0:
            write_out_to_single_file(toks, ana, fn, single_f,
                                     write_header=True, rids=print_rule_ids)
            write_out_to_single_file(toks, ana, fn, tsvfile,
                                     write_header=True, tsv=True,
                                     rids=print_rule_ids)
        else:
            write_out_to_single_file(toks, ana, fn, single_f,
                                     rids=print_rule_ids)
            write_out_to_single_file(toks, ana, fn, tsvfile, tsv=True,
                                     rids=print_rule_ids)
        dones += 1
        # standoff annotations
        write_standoff(ana, fn, standoff, rids=print_rule_ids)
        if logfh is not None:
            logfh.flush()
    if logfh is not None:
        logfh.close()
    os.system("cut -f1-6 {} > {}".format(standoff, norules))
    print u"- Wrote single file to [{}]".format(single_f)
    print u"- Wrote single file TSV to [{}]".format(tsvfile)
    print u"- Wrote standoff to [{}]".format(standoff)
    print u"- Wrote norules to [{}]".format(norules)
    print u"- Wrote log to [{}]".format(logfn)


def main():
    argus = run_argparse()
    if argus.batchname == "DEF":
        print "Enter a valid batch name (using the default " + \
              "'DEF' is not allowed)"
        sys.exit(2)
    if 'customsort' in argus and argus.customsort:
        sorter = argus.sorter
    else:
        sorter=None
    if 'restrictfiles' in argus and argus.restrictfiles:
        shortlist = argus.keepfilelist
    else:
        shortlist = None
    if 'logdetails' in argus and argus.logdetails:
        logpath = argus.logfile
    else:
        logpath = None
    printruleids = argus.ruleid
    run_dir(argus.inname, argus.outdir, argus.singlefile,
            argus.nlpdir, argus.lang, argus.constituency, argus.dependency,
            argus.m14, logpath,
            sorter_list_fn=sorter, restrict_to_list_fn=shortlist,
            print_rule_ids=printruleids)


if __name__ == "__main__":
    main()
