# coding: utf-8

"""
Compare standoff with rule-ids with reference, output whether rule matched span and type
besides accuracy per rule.
@note: Assumes a single type per span. May need to refactor to treat multiple types per span.
"""

__author__ = 'Pablo Ruiz'
__date__ = '28/06/17'
__email__ = 'pabloruizfabo@gmail.com'


import argparse
import codecs


RULE_SORTER = ["t", "pp", "pc", "pd", "cp", "cc", "cd", "ld"]
HEADER = ["poemid", "start", "end", "etype", "dummy", "etype",
          "ruleid", "spanok", "typeok"]
DEBUG = True


def run_argparse():
    """CLI parser"""
    parser = argparse.ArgumentParser(description="Evaluates enjambment detection rules")
    parser.add_argument('-i', '--infile', help='Input file')
    parser.add_argument('-r', '--rffile', help='Reference file')
    parser.add_argument('-o', '--outfile', help='Output file')
    parser.add_argument('-s', '--stats', help='Stats file')
    return parser.parse_args()


# Acosta,_Ignacio_María__099~~Al_plan_de_Matanzas__0334   10      11      oracional
#        1       oracional       c001

def read_data(dt, mode):
    """
    Output this: {fn: {b, e: {etype: etype, rid: rid}}} or without the rid
    if it's a reference set
    """
    assert mode in ("ref", "res")
    di = {}
    with codecs.open(dt, "r", "utf8") as dtf:
        line = dtf.readline()
        while line:
            sl = line.strip().split("\t")
            fn, beg, end, etype, = (sl[0], int(sl[1]), int(sl[2]), sl[3])
            if mode == "res":
                rid = sl[6]
            di.setdefault(fn, {})
            di[fn].setdefault((beg, end), {"etypes": []})
            di[fn][(beg, end)]["etypes"].append(etype)
            if mode == "res":
                di[fn][(beg, end)].update({"rids": []})
                di[fn][(beg, end)]["rids"].append(rid)
            line = dtf.readline()
    return di


def compare(rdi, sdi):
    """
    Compare system and reference results
    @param rdi: Dictionary with reference results.
    @param sdi: Dictionary with system ressults.
    @return: Dictionary with analysis per rule.
    @rtype: dict
    """
    rulean = {}
    for fn, results in sdi.items():
        # file has annotations in system but not in reference
        if fn not in rdi:
            for span, infos in results.items():
                # spaneval key with a 0 value indicates span error
                results[span].update({"spaneval": 0, "typeseval": []})
                for rid in infos["rids"]:
                    rulean.setdefault(rid, {"ok": 0, "ko": 0})
                    rulean[rid]["ko"] += 1
                    # typeseval key with 0 value indicates type error
                    results[span]["typeseval"].append(0)
        else:
            # compare spans when filename both in ref and res
            for span2, infos2 in results.items():
                # span in system but not in reference
                if span2 not in rdi[fn]:
                    results[span2].update({"spaneval": 0, "typeseval": []})
                    for rid in infos2["rids"]:
                        rulean.setdefault(rid, {"ok": 0, "ko": 0})
                        rulean[rid]["ko"] += 1
                        results[span2]["typeseval"].append(0)
                else:
                    # compare annotations when spans both in ref and res
                    for rid in infos2["rids"]:
                        rulean.setdefault(rid, {"ok": 0, "ko": 0})
                        # add hits
                        rulean[rid]["ok"] += \
                            len(set(infos2["etypes"]).intersection(
                                set(rdi[fn][span2]["etypes"])))
                        # add errors
                        rulean[rid]["ko"] += \
                            len(set(infos2["etypes"]).difference(
                                set(rdi[fn][span2]["etypes"])))
                        rulean[rid]["ko"] += \
                            len(set(rdi[fn][span2]["etypes"]).difference(
                                set(infos2["etypes"])))
                        # add analysis to standoff results
                        # for types eval, compare zipped lists elementwise
                        assert len(infos2["etypes"]) == len(rdi[fn][span2]["etypes"])
                        results[span2].update({"spaneval": 1,
                            "typeseval": [1 if systype == reftype else 0
                                for (systype, reftype) in
                                zip(infos2["etypes"], rdi[fn][span2]["etypes"])]})
    return rulean


def write_compared_standoff(di, ifn, ofn):
    """
    Write out standoff annotations with extra columns indicating
    whether the span and type match or not.
    @param di: dict with compared results
    @param ifn: input file, read here just to obtain original poem order
    to respect it when writing out
    @param ofn: path to output file
    @note: assumes one type per span
    """
    # read input file to get filename order
    filename_order = []
    with codecs.open(ifn, "r", "utf8") as infi:
        line = infi.readline()
        while line:
            sl = line.strip().split("\t")
            filename_order.append(sl[0])
            line = infi.readline()
    # write out compared results
    with codecs.open(ofn, "w", "utf8") as oufi:
        ols = ["\t".join(HEADER)]
        for fn, infos in sorted(
                di.items(), key=lambda fn2infos: filename_order.index(fn2infos[0])):
            for span, infos2 in sorted(infos.items()):
                ol = [fn, span[0], span[1],
                      ";".join(infos2["etypes"]), 1,
                      ";".join(infos2["etypes"]),
                      ";".join(infos2["rids"]),
                      infos2["spaneval"],
                      ";".join([unicode(x) for x in infos2["typeseval"]])]
                ols.append("\t".join([unicode(x) for x in ol]))
        oufi.write("\n".join(ols))
    print u"- Wrote evaluated standoff results to [{}]".format(ofn)


def write_per_rule(di, ofn):
    """
    Write accuracy stats for each rule
    Sort order as in L{RULE_SORTER}
    """
    header = ["rule", "#", "#ok", "#ko", "%ok", "%ko"]
    ols = []
    with codecs.open(ofn, "w", "utf8") as oufi:
        oufi.write("".join(("\t".join(header), "\n")))
        for ke, vals in sorted(di.items(),
            key=lambda tu: (RULE_SORTER.index(tu[0][0:2]), int(tu[0][2:]))):
            total = vals["ok"] + vals["ko"]
            ol = [ke, total, vals["ok"], vals["ko"],
                  100 * (float(vals["ok"]) / total),
                  100 * (float(vals["ko"]) / total)]
            ols.append("\t".join([unicode(x) for x in ol]))
        oufi.write("\n".join(ols))
    print u"- Wrote stats per rule to [{}]".format(ofn)


def main():
    if DEBUG:
        global ref
        global sr
        global ana
    argus = run_argparse()
    ref = read_data(argus.rffile, "ref")
    sr = read_data(argus.infile, "res")
    ana = compare(ref, sr)
    write_compared_standoff(sr, argus.infile, argus.outfile)
    write_per_rule(ana, argus.stats)


if __name__ == "__main__":
    main()