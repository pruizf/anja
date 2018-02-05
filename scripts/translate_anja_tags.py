"""
Translate enjambment tags in results files or in evaluation files using config info.
"""

__author__ = 'Pablo Ruiz'
__date__ = '04/11/16'
__email__ = 'pabloruizfabo@gmail.com'


import codecs
import os
import re

# add current dir
import inspect
import sys

here = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
sys.path.append(here)
sys.path.append(os.path.join(here, os.pardir))

# app specific imports
import config as cfg
import utils as ut


try:
    infn = sys.argv[1]
except IndexError:
    infn = ""

ofn = infn + ".trans.txt"


def translate(cf, ffn):
    etags = ut.load_enca_tag_translations_as_regex(cf)
    with codecs.open(ffn, "r", "utf8") as ifd,\
         codecs.open(ofn, "w", "utf8") as ofd:
        line = ifd.readline()
        while line:
            nline = ut.apply_enca_tag_translation_dict_with_regex(etags, line)
            ofd.write(nline)
            line = ifd.readline()


if __name__ == "__main__":
    translate(cfg, infn)




