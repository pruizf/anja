# ANJA

**A**utomatic e**NJ**ambment **A**nalysis in Spanish.

Enjambment takes place when a syntactic unit is broken up across two lines of poetry, which can give rise to different stylistic effects and contributes to poetry's interplay between meter and meaning. 

ANJA performs enjambment detection in Spanish, via rules, based on part-of-speech tagging, and constituent and dependency parsing.

For a full description of the enjambment types the system detects, see the [project's site](https://sites.google.com/site/spanishenjambment/)

##Enjambment Detection Workflow
![System Workflow Diagram](https://sites.google.com/site/spanishenjambment/system-details/enca_system_workflow_noblank.png)


## Requirements
- Python 2.7
- [IXA Pipes](http://ixa2.si.ehu.es/ixa-pipes/) NLP toolkit, including its [dependency/Semantic Role Labeling parser](https://github.com/newsreader/ixa-pipe-srl).
- Java 1.7+ to run IXA Pipes
- [KafNafParserPy](https://github.com/cltl/KafNafParserPy). Needs to be Python-importable by the tool (i.e. you need to be able to do something like 'import KafNafParserPy as knp' from a Python script).


## Usage

For a simple use with the most common options, once IXA Pipes has been installed (see [instructions](http://ixa2.si.ehu.es/ixa-pipes/)), and the paths in _run_nlp.sh_ point to its modules, you can test the tool on the files in _data/sample/in_, using the `run_anja.py` script, from the script's directory, like in this command:
 
    python run_anja.py -b batch-001 -i data/sample/in -n data/sample/out/nlp
    -p data/sample/out/pos -o data/sample/out/out
 
That will execute `run_anja.py` using _batch-001_ as the batch name, outputting the full NLP results to _data/sample/out/nlp_, the PoS-tags used by ANJA to _data/sample/out/pos_ and the final enjambment results to _data/sample/out/out_.

For more detailed usage, the modules can be used independently as long as the input requirements are respected.

Each module has a help file, that can be accessed with the `-h` option: `module_name -h`
 
For instance, the help file for `run_anja.py` is the following:

    :::text
    usage: run_anja.py [-h] [-b BATCHNAME] [-i INNAME] [-e PREPRO] [-l LOGDIR]
                       [-n NLPDIR] [-p POSDIR] [-o OUTDIR]
    Apply enjambment detection to NLP output
    
    optional arguments:
      -h, --help            show this help message and exit
      -b BATCHNAME, --batch BATCHNAME
                            String representing the name of the batch. (Used to
                            name output files etc.). (default: DEF)
      -i INNAME, --input INNAME
                            Input dir (contains PoS and term-id annotations
                            (default: ../enca2texts/enca2out/DEF/DEF_postid)
      -e PREPRO, --prepro PREPRO
                            Poem without linebreaks (default:
                            data/sample/out/prepro)
      -l LOGDIR, --logdir LOGDIR
                            Stores line positions for each line in corpus
                            (default: data/sample/out/logs)
      -n NLPDIR, --nlpdir NLPDIR
                            Dir containing NLP output (NAF from IXA pipes)
                            (default: ../enca2texts/enca2out/DEF/DEF_parsed)
      -p POSDIR, --posdir POSDIR
                            Output dir, will contain poem with each tokenannotated
                            with a POS and term-id (default:
                            ../enca2texts/enca2out/DEF/DEF_postid)
      -o OUTDIR, --outdir OUTDIR
                            Output dir: poem with encabalgamiento annots (default:
                            ../../enca2texts/enca2out/DEF)


If no paths are given, the Python modules provide default input and output locations based on the batchname argument (see the help for each module).


## Brief description of the modules and other scripts

### Managing the NLP web-services

- **run_nlp.sh** requires a directory (with subdirectories or not) where each file contains one poem. It outputs NAF produced by IXA pipes, calling its web-services. All poems are output to a single directory.
 
- **stop_ws.sh**: Stops the web-services started by *run_nlp.sh* 

### ANJA workflow

- **prepro/prepro.py** takes plain text poems and will output (1) a list of the positions (offsets) for each poem's line, and a version of the poem where the complete text is on a single line. This is a preprocessing step intended to make NLP analysis easier. 

- **extract_pos.py** requires NAF files (e.g. from IXA pipes) for each poem and creates a human readable pos-tagged version (optionally with term-ids) for each poem.

- **detect.py** requires the output of *extract_pos.py*. It contains enjambment detection **rules** and runs enjambment detection, creating the outputs described below. 

### Other

- **scripts/translate_anja_tags.py**: Enjambment tag names (see [here](https://sites.google.com/site/spanishenjambment/enjambment-types#TOC-Types-detected-by-our-system) for a list) are output in Spanish. An easy way to translate them into English is with the _scripts/translate_anja_tags.py_ module. 

## Result format

- Many more details about this are given in the [project's site](https://sites.google.com/site/spanishenjambment/annotation-and-result-format)

- In the output folder (see _data/sample/out/out_) in the repository, you'll see an individual file for each input file, besides aggregated results for the complete batch.

- The aggregated files contain (by default) the batch name and _corpus_results_ in their name. Several formats are output:
    - **.txt**: raw output (can be used for grepping), containing poem-line and enjambment tags (if any)
    
    - **.tsv**: to open with a spreadsheet, since has quoted multi-line cells so that some infos are read more easily in some spreadsheet softwares.
    
    - **\_sto.txt**: standoff annotations, i.e. the line numbers and enjambment tags, besides the ID for the ANJA rule that detected the enjambment (see _detect.py_)
    
    - **\_sto_norules.txt**: standoff annotations, but without the rule-IDs.


- Intermediate steps in the processing are also output. For instance, the NLP results that enjambment detection is based on are at _data/sample/out/nlp_ in the repository). Other directories under _data/sample/out_ (_prepro_, _pos_, _logs_) are also intermediate outputs)


## Citing

Ruiz Fabo, Pablo, Clara Martinez Canton, Thierry Poibeau and Elena Gonzalez-Blanco. (2017). Enjambment detection in a large diachronic corpus of Spanish sonnets. In _LaTeCH-CLFL 2017, Joint SIGHUM Workshop on Computational Linguistics for Cultural Heritage, Social Sciences, Humanities and Literature_, pp. 27-32. Vancouver, Canada. Association for Computational Linguistics.