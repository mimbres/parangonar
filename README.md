Parangonar
==========

**Parangonar** is a Python package for note alignment of symbolic music. 
**Parangonar** uses [Partitura](https://github.com/CPJKU/partitura) as file I/O utility.
Note alignments produced py **Parangonar** can be visualized using the 
web tool [Parangonda](https://sildater.github.io/parangonada/)


Installation
==========

The easiest way to install the package is via `pip` from the [PyPI (Python
Package Index)](https://pypi.org/project/parangonar/>):
```shell
pip install parangonar
```
This will install the latest release of the package and will install all dependencies automatically.


Quickstart
==========

The following code loads the contents of a a previously aligned performance
and score alignment file (encoded in the [match file format](https://arxiv.org/abs/2206.01104)). 

A new alignment is computed using a hierarchical DTW-based note matcher and the resulting
alignment are compared to the ground truth:

```python
import parangonar as pa
import partitura as pt

perf_match, groundtruth_alignment, score_match = pt.load_match(
    filename= pa.EXAMPLE,
    create_score=True
)

# compute note arrays from the loaded score and performance
pna_match = perf_match.note_array()
sna_match = score_match.note_array()

# match the notes in the note arrays
sdm = pa.AutomaticNoteMatcher()
pred_alignment = sdm(sna_match, 
                     pna_match,
                     verbose_time=True)

# compute f-score and print the results
print('------------------')
types = ['match','insertion', 'deletion']
for alignment_type in types:
    precision, recall, f_score = pa.fscore_alignments(pred_alignment, 
                                                      groundtruth_alignment, 
                                                      alignment_type)
    print('Evaluate ',alignment_type)
    print('Precision: ',format(precision, '.3f'),
          'Recall ',format(recall, '.3f'),
          'F-Score ',format(f_score, '.3f'))
    print('------------------')
```


Aligning MusicXML Scores and MIDI Performances
==========


```python
import parangonar as pa
import partitura as pt

score = pt.load_score(filename= 'path/to/score_file')
performance = pt.load_performance_midi(filename= 'path/to/midi_file')

# compute note arrays from the loaded score and performance
pna = performance.note_array()
sna = score.note_array()

# match the notes in the note arrays
sdm = pa.AutomaticNoteMatcher()
pred_alignment = sdm(sna_match, pna_match)
```

File I/O for note alignments
==========

```python
import partitura as pt
import parangonar as pa

# load note alignments of the asap dataset: 
# https://github.com/CPJKU/asap-dataset/tree/note_alignments
alignment = pt.io.importparangonada.load_alignment_from_ASAP(filename= 'path/to/note_alignment.tsv')

# export a note alignment for visualization with parangonada:
# https://sildater.github.io/parangonada/
pa.match.save_parangonada_csv(alignment, 
                            performance_data,
                            score_data,
                            outdir="path/to/dir")

# import a corrected note alignment from parangonada:
# https://sildater.github.io/parangonada/
alignment = pt.io.importparangonada.load_parangonada_alignment(filename= 'path/to/note_alignment.csv')
```



Anchor Point Alignment Example
==========

```python
import parangonar as pa
import partitura as pt

perf_match, groundtruth_alignment, score_match = pt.load_match(
    filename= pa.EXAMPLE,
    create_score=True
)

# compute note arrays from the loaded score and performance
pna_match = perf_match.note_array()
sna_match = score_match.note_array()

# compute synthetic anchor points every 4 beats
nodes = pa.match.node_array(score_match[0], 
                   perf_match[0], 
                   groundtruth_alignment,
                   node_interval=4)

# match the notes in the note arrays
apdm = pa.AnchorPointNoteMatcher()
pred_alignment = apdm(sna_match, 
                     pna_match,
                     nodes)

# compute f-score and print the results
print('------------------')
types = ['match','insertion', 'deletion']
for alignment_type in types:
    precision, recall, f_score = pa.fscore_alignments(pred_alignment, 
                                                      groundtruth_alignment, 
                                                      alignment_type)
    print('Evaluate ',alignment_type)
    print('Precision: ',format(precision, '.3f'),
          'Recall ',format(recall, '.3f'),
          'F-Score ',format(f_score, '.3f'))
    print('------------------')
```

Visualize Alignment
==========
```python
import parangonar as pa
import partitura as pt

perf_match, alignment, score_match = pt.load_match(
    filename= pa.EXAMPLE,
    create_score=True
)
pna_match = perf_match.note_array()
sna_match = score_match.note_array()

# show or save plot of note alignment
pa.plot_alignment(pna_match,
                sna_match,
                alignment,
                save_file = False)
```

License
=======

The code in this package is licensed under the Apache 2.0 License. For details,
please see the [LICENSE](LICENSE) file.
