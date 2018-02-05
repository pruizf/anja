"""Common functions to be used elsewhere in app"""

__author__ = 'Pablo Ruiz'
__date__ = '10/08/16'
__email__ = 'pabloruizfabo@gmail.com'


import codecs
from lxml import etree
import os
import re
from string import zfill


# add current dir to sys.path
import inspect
import sys

basedir = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
sys.path.append(basedir)

import config as cfg


nspaces = {'tei': 'http://www.tei-c.org/ns/1.0'}


def read_dir_into_ttl2txt_dict(idir):
    """
    Read a directory of plain text poems where the filename represents a title
    into a title2text dict.
    Filename format (not exploiting the format for now, here just for info):
        - AuthorLast_First__AuthorID~~Title__TitleID.txt or
        - AuthorLast_First__AuthorID~~Title__TitleID__Subtitle__SubtitleID.txt
    """
    ttl2txt = {}
    for fn in sorted(os.listdir(idir)):
        ffn = os.path.join(idir, fn)
        with codecs.open(ffn, "r", "utf8") as ifd:
            # only strip newline in case leading/trailing spaces in text
            #text = [ll.strip("\r\n") for ll in ifd]
            text = [ll.strip() for ll in ifd]
            if len(text) == 0:
                print u"! Skipping empty text [{}]".format(fn)
            try:
                assert fn not in ttl2txt
            except AssertionError:
                print u"! DupFileName in [{}]".format(fn)
            ttl2txt.setdefault(fn, text)
    return ttl2txt


def walk_dir_into_ttl2text(idir):
    """
    Read a directory of TEI XML poems where the filename represents author name
    into a title2text dict.
    Filename format (not exploiting the format for now, here just for info) is
    the same as L{read_dir_into_ttl2txt_dict}, but with a dummy title id and with
    an author id equal to the author name, since here the authors are unambiguous
    and will then disambiguate poem names:
        - AuthorLast_First__AuthorID~~Title__TitleID.txt or
        - AuthorLast_First__AuthorID~~Title__TitleID__Subtitle__SubtitleID.txt
    """
    title2text = {}
    for dname, subdir_list, flist in os.walk(idir):
        print "= Processing dir [{}]".format(dname)
        for fname in [ff for ff in flist if ff.endswith(".xml")]:
            title, llist = tei_lgl2text(
                os.path.join(dname, fname))
            get_au_tid = re.search(ur"^([^\n]+)_([0-9]+).*xml$", fname)
            assert len(get_au_tid.groups()) == 2
            auname, tid = get_au_tid.group(1), get_au_tid.group(2)
            #import pdb;pdb.set_trace()
            norfname = ur"{}__{}~~{}__{}.txt".format(
                auname, auname, title.strip()[0:40].replace(
                    " ", "_"), zfill(tid, 3))
            title2text[norfname] = llist
    return title2text


def tei_lgl2text(xfn, mynspaces=nspaces):
    """
    From TEI XML, get text in l elements under an lg, inserting a line-break
    after each lg.
    @param xfn: full path to TEI XML file
    @param mynspacces: namespace
    @return: tuple with title and lines of the poem
    @rtype: tuple
    """
    lines = []
    tree = etree.parse(xfn)
    try:
        ttl = tree.xpath("//tei:text/tei:body/tei:head/tei:title/text()",
                         namespaces=mynspaces)[0]
    except IndexError:
        ttl = ""
    lgs = tree.xpath("//tei:lg", namespaces=mynspaces)
    for lg in lgs:
        lgls = lg.xpath(".//tei:l/text()", namespaces=mynspaces)
        lines.extend(lgls)
        #lines.append("\n")
        lines.append("")
    return ttl, lines


def write_dict_sorted(t2t, odir):
    """
    Write one poem per file
    @param t2t: dict of texts hashed by title
    @param odir: output dir to write the poems to
    """
    for title in sorted(t2t):
        print ur"- Writing {}".format(title)
        with codecs.open(os.path.join(
            odir, ur"{}.txt".format(title)), "w", "utf8") as outf:
            outf.write(u"{}\n".format(title))
            outf.write("\n".join(t2t[title]))


def escape4regex(txt):
    """
    Escape text so that can search it as a regex pattern
    @param txt: the text to escape
    """
    txt = txt.replace("(", r"\(")
    txt = txt.replace(")", r"\)")
    txt = txt.replace("?", r"\?")
    txt = txt.replace("+", r"\+")
    txt = txt.replace(".", r"\.")
    return txt


def merge_lines_and_get_line_positions(t2t, odir, logdir, batchname):
    """
    Remove line-breaks from poems so that can run nlp tools on them, but
    write out line positions because need to know later where end of the line
    was, to test for encabalgamiento.
    @note: Only searches positions for non-empty lines, but empty lines are
    kept in the text used for searching positions in, so that positions
    do reflect actual offsets in texts with empty lines.
    @param t2t: dict of texts hashed by title
    @param odir: dir to write the files with text without linebreaks
    @param logdir: dir to write position info to
    @param batchname: used for filenames, to create batch-specific outputs
    """
    #TODO: may not be necessary to write everything on one line
    #      (NLP may be fine with text as is)
    print "- Merging lines and getting line positions"
    linepositions = {}
    for ti, text in t2t.items():
        linepositions.setdefault(ti, {})
        # text including empty lines
        ntext = " ".join(text)
        if len(ntext.strip()) == 0:
            print u"! Empty text".format(ti)
            continue
        # text with empty lines removed, to avoid incorrect line numbers
        text_without_empty_lines = [li for li in text if len(li) > 0]
        for nbr, line in enumerate(text_without_empty_lines):
            # store more than one position for a line that repeats, but
            # not finding which line numbers are equivalent for now
            eline = escape4regex(line)
            # search, in text including empties, positions for non-empties
            positions = [(m.start(), m.end())
                         for m in re.finditer(eline, ntext)
                         if len(eline) > 0]
            linepositions[ti][nbr] = positions
        try:
            onelinefn = ti.decode("utf8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            onelinefn = ti
        with codecs.open(os.path.join(odir, u"{}_oneline.txt".format(
                onelinefn)), "w", "utf8") as outf:
            outf.write(ntext)
    with codecs.open(os.path.join(logdir, cfg.line_positions.format(
            batch=batchname)), "w", "utf8") as logf:
        for ti, l2posis in sorted(linepositions.items()):
            for lnbr, posis in sorted(l2posis.items()):
                out_posis = ["{},{}".format(str(posi[0]), str(posi[1]))
                             for posi in posis]
                out_posis = "~".join(out_posis)
                # compatibility across corpora
                if not ti.endswith(".txt"):
                    ti += ".txt"
                try:
                    logf.write(u"{}\t{}\t{}\n".format(ti.decode("utf8"),
                                                      lnbr + 1, out_posis))
                except (UnicodeDecodeError, UnicodeEncodeError):
                    logf.write(u"{}\t{}\t{}\n".format(ti,
                                                      lnbr + 1, out_posis))


def read_pos_tagged_poem(inf):
    """
    Read pos-tagged poem, written as in L{}
    and return tokens with pos and term-id
    @param inf: input file
    """
    tokpoem = []
    with codecs.open(inf, "r", "utf8") as fni:
        lines = fni.readlines()
        for ll in lines:
            toks = re.findall(cfg.TOKRE, ll.strip())
            tokpoem.append(toks)
    return tokpoem


def file_to_ordered_list(sorter):
    """Return a list that will be used for custom sorting agaisnt it"""
    with codecs.open(sorter, "r", "utf8") as sd:
        return [l.strip() for l in sd if not l.startswith("#")]


def read_suplemento(cf):
    """
    Read and return the dictionary that contains verbs taking 'suplemento'
    (a lexically determined prepositional argument)
    https://es.wikipedia.org/wiki/Complemento_de_r%C3%A9gimen
    @param cf: config for app, at L{config.py}
    """
    di = {}
    with codecs.open(cf.suplemento) as fd:
        line = fd.readline()
        while line:
            if line.startswith("#"):
                line = fd.readline()
                continue
            add_prep_2 = False
            # read dict
            sl = line.strip().split("\t")
            lemma, lemma2, prep = sl[0], re.sub("rse$", "r", sl[0]), sl[1]
            # contracted preps
            if prep in ("de", "a"):
                prep2 = prep + "l"
            else:
                prep2 = prep
            if prep != prep2:
                add_prep_2 = True
            # populate
            di.setdefault(lemma, set()).add(prep)
            if add_prep_2:
                di.setdefault(lemma, set()).add(prep2)
            if lemma != lemma2:
                di.setdefault(lemma2, set()).add(prep)
                if add_prep_2:
                    di.setdefault(lemma2, set()).add(prep2)
            # add participles (in case pos-tagging errors)
            if lemma2[-2:] in ("er", "ir"):
                partic_m = re.sub(r"[ei]r$", "ido", lemma2)
                partic_f = re.sub(r"[ei]r$", "ida", lemma2)
            elif lemma2.endswith("ar"):
                partic_m = re.sub("r$", "do", lemma2)
                partic_f = re.sub("r$", "da", lemma2)
            di.setdefault(partic_m, set()).add(prep)
            di.setdefault(partic_f, set()).add(prep)
            if add_prep_2:
                di.setdefault(partic_m, set()).add(prep2)
                di.setdefault(partic_f, set()).add(prep2)
            line = fd.readline()
    return di


def read_periphrases(cf):
    """
    Read and return the dictionary that contains verb periphrases, given
    in config module 'cf'.
    @param cf: config for app, at L{config.py}
    Periphrases rules in L{detect_enca} are triggered if matching dictionary
    elements (dict returned by this function) as follows:
        - ponly: the preposition following the auxiliary is enough
        - tonly: the given type (inf, ger, par) of non-personal tense
                 following the auxiliary is enough
        - pandt: you need a combination of a prep + tense following the aux
                 to trigger the rule (in practice may accept any series of
                 tokens matching, e.g. 'va y hace...')
    """
    di = {}
    with codecs.open(cf.periphrases, "r", "utf8") as fd:
        line = fd.readline()
        while line:
            if line.startswith("#"):
                line = fd.readline()
                continue
            # aux verb, prep (if any), tense (inf, ger, par) for non-personal form
            aux, prep, npte = line.strip().split(";")
            # prep-only, tense-only or both prep and tense
            di.setdefault(aux, {"ponly": set(), "tonly": set(), "pandt": set()})
            if len(prep) == 0:
                di[aux]["tonly"].add(npte)
                # for tagging errors, add 'adj' if participle
                if npte == "Vpar":
                    di[aux]["tonly"].add("G")
            elif len(prep) > 0 and npte == "Vinf":
                di[aux]["ponly"].add(prep)
            elif len(prep) > 0 and npte != "Vinf":
                di[aux]["pandt"].add((prep, npte))
                # for tagging errors, add 'adj' if participle
                if npte == "Vpar":
                    di[aux]["pandt"].add((prep, "G"))
            line = fd.readline()
    return di


def normalize_enca_types(cf, etag):
    """
    Given config, replace an enjambemnt type tag by another one
    """
    reps = []
    with codecs.open(cf.entagnorm, "r", "utf8") as fd:
        line = fd.readline()
        while line:
            if line.startswith("#"):
                line = fd.readline()
                continue
            sl = line.strip().split("\t")
            assert sl[0] not in reps
            reps.append((sl[0], sl[1]))
            line = fd.readline()
    for context, rep in reps:
        if re.search(context, etag):
            etag = re.sub(context, rep, etag)
    return etag


def grep_file_list_in_results_file(fns, rfn):
    """
    Given filelist fns and results filename rfn, grep in the results
    for the filenames in the list. Return list of matches.
    """
    lines = []
    with codecs.open(rfn, "r", "utf8") as fd:
        line = fd.readline()
        while line:
            for fn in fns:
                # _annot suffix used in fns in app
                if line.startswith(fn.replace("_annot", "")):
                    lines.append(line.strip())
            line = fd.readline()
    return lines


def grep_file_list_in_results_lines(fns, rfl):
    """
    Given filelist fns and a list of lines with results rfl,
    grep in the results for the filenames in the list.
    Return list of matches.
    """
    lines = []
    for fn in fns:
        for ll in rfl:
            if ll.startswith(fn.replace("_annot", "")):
                lines.append(ll.strip())
    return lines


def read_filenames_to_restrict_detection(lfn):
    """
    Read and return a list of file names (lfn), rendering names
    in format required by app
    """
    fns = file_to_ordered_list(lfn)
    nor_fns = []
    for fn in fns:
        #assert fn.endswith(".txt")
        # file naming conventions in app
        if not fn.endswith(".txt"):
            fn = "".join((fn, "_annot.txt"))
        elif not fn.endswith("_annot.txt"):
            fn = fn.replace(".txt", "_annot.txt")
        nor_fns.append(fn)
    return nor_fns


def load_enca_tag_translations(cf):
    """
    Load translation equivalents for enjambment tags, as per path
    in config cf
    """
    with codecs.open(cf.tag_translation, "r", "utf8") as infd:
        rows = (line.strip().split("\t") for line in infd
                if not line.startswith("#"))
        tagt = {row[0]: row[1] for row in rows}
    return tagt


def load_enca_tag_translations_as_regex(cf):
    """
    Load translation equivalents for enjambment tags, as per path
    in config cf, as regexes, to do full-word-only replacements
    """
    with codecs.open(cf.tag_translation, "r", "utf8") as infd:
        rows = (line.strip().split("\t") for line in infd
                if not line.startswith("#"))
        tagt = {re.compile(
            ur"(^|\W){}(\W|$)".format(row[0])): row[1] for row in rows}
    return tagt


def translate_enca_tag(tag, trdi):
    """Translate a tag (tag) based on a translation dict (trdi)"""
    if tag not in trdi:
        print u"{} not in translation dictionary".format(tag)
        sys.exit(2)
    return trdi[tag]


def apply_enca_tag_translation_dict_with_regex(trdi, txt):
    """Do the tag translation applying regexes"""
    nomatch = True
    ntxt = txt
    for tagre, trans in trdi.items():
        # recursive: in '_inline.txt' you can have > 1 tag per line
        txt = ntxt
        match = re.search(tagre, txt)
        if match:
            ntxt = re.sub(tagre, u"{}{}{}".format(
                match.group(1), trdi[tagre], match.group(2)), txt)
            # max two matches per line
            ntxt = re.sub(tagre, u"{}{}{}".format(
                match.group(1), trdi[tagre], match.group(2)), ntxt)
            nomatch = False
    if nomatch:
        return txt
    return ntxt


def update_span(di, idx, etype, rid, dn, m14):
    """
    Add an enjambment annotation to a line span.
    @param di: dict with enjambment annotations. Positions as keys.
    @type di: dict
    @param idx: line number where enjambed span starts
    @type idx: int
    @param etype: enjambment type
    @type etype: unicode
    @param rid: rule id
    @type rid: str
    @param dn: set with lines that have been done
    @type dn: set
    @param m14: allow rule application beyond 14 lines
    (actually we always allow 17 lines for estrambote cases, so > 17)
    """
    if idx not in dn:
        di.setdefault(idx, [])
        di.setdefault(idx+1, [])
        di[idx].append(("B", etype, rid))
        di[idx+1].append(("I", etype, rid))
        # remove "O" tags if there actually is an annotation
        for ctr in (idx, idx+1):
            #import pdb;pdb.set_trace()
            filt = [an for an in di[ctr] if an[0] != "O"]
            di[ctr] = filt
        dn.add(idx)
        # prevent problems on last line-pair of sonnet
        #   treats 'estrambote' cases
        if not m14 and idx in (13, 16):
            # prevent starting span on last line
            filt = [an for an in di[idx] if an[0] != "B"]
            di[idx] = filt


def logdep(fn, tree, lgfh, idx, rid, cur=(None, None, None),
           nxt=(None, None, None), pen=(None, None, None), sec=(None, None, None),
           headdep=None):
    """
    Log details for rules involving dependency info.
    @param fn: filename
    @param tree: NAF tree for NLP results
    @type tree: L{KafNafParserPy.KafNafParser}
    @param lgfh: open file handle to write (as a log)
    @param idx: line index (add 1 if want 1-indexed instead of 0-indexed)
    @param rid: rule-id
    @param cur: triple (word-form, pos, term-id) for current line's final token
    (see L{detect_enca.cwf}, L{detect_enca.cpos}, L{detect_enca.ctid})
    @param nxt: triple (word-form, pos, term-id) for following line's final token
    @param pen: triple (word-form, pos, term-id) for current line's penult token
    @param sec: triple (word-form, pos, term-id) for following line's second token
    @param headdep: head/dependent pair from tree's dependency layer
    @type headdep: L{KafNafParserPy.dependency_data.Cdependency}
    @note: .get_dependencies() on the tree is a generator, and tree.dependency_layer
    gives you a L{KafNafParserPy.dependency_data.Cdependencies}
    """
    pi = u"pen=[{}, {}, {}]".format(pen[0], pen[1], pen[2])
    ci = u"cur=[{}, {}, {}]".format(cur[0], cur[1], cur[2])
    ni = u"nxt=[{}, {}, {}]".format(nxt[0], nxt[1], nxt[2])
    si = u"sec=[{}, {}, {}]".format(sec[0], sec[1], sec[2])
    # figure out head/dependent tokens
    htok = [tok for tok in tree.text_layer if tok.get_id() ==
            tree.term_layer.get_term(headdep.get_from()).get_span().get_span_ids()[0]
           ][0]
    hwf = htok.get_text()
    hpos = tree.term_layer.get_term(headdep.get_from()).get_pos()
    dwf = [tok for tok in tree.text_layer if tok.get_id() ==
           tree.term_layer.get_term(headdep.get_to()).get_span().get_span_ids()[0]
          ][0].get_text()
    dpos = tree.term_layer.get_term(headdep.get_to()).get_pos()
    func = headdep.get_function()
    hdi = u"hea=[{}, {}, {}] | dep=[{}, {}, {}] | func=[{}]".format(
        hwf, hpos, headdep.get_from(), dwf, dpos, headdep.get_to(), func)
    # get sentence
    sent_nbr = htok.get_sent()
    sent_tokens = [[tok.get_text(), tok.get_id()] for tok in tree.text_layer
                   if tok.get_sent() == sent_nbr]
    sent_terms = [[tk[0],
                   #[term.get_pos() for term in tree.term_layer
                   # if term.get_span().get_span_ids()[0] == tk[1]][0],
                   [term.get_id() for term in tree.term_layer
                    if term.get_span().get_span_ids()[0] == tk[1]][0]]
                  for tk in sent_tokens]
    sent_terms_with_line_boundary = [(te[0], u"{}****".format(te[1]))
                                     if te[1] == cur[2] else (te[0], te[1])
                                     for te in sent_terms]
    # write out
    if isinstance(fn, str):
        fn = fn.decode("utf8")
    out_sent = " ".join([u"{{{} {}}}".format(te[0], te[1])
                         for te in sent_terms_with_line_boundary])
    ol = u"{} [{}] [{}] {} | {} | {} | {} || {} || {}\n".format(
        unicode(fn), idx, rid, pi, ci, ni, si, hdi, out_sent)
    lgfh.write(ol)
