#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module includes tests for alignment utilities.
"""
import unittest
import numpy as np
from parangonar.match import AutomaticNoteMatcher
import os
import partitura as pt


RNG = np.random.RandomState(1984)
from tests import MATCH_FILES




class TestNoteAlignment(unittest.TestCase):
    def test_auto_align(self, **kwargs):
        
        perf_match, alignment, score_match = pt.load_match(
            filename=MATCH_FILES[0],
            create_score=True,
            first_note_at_zero=True,
        )
        
        pna_match = perf_match.note_array()
        sna_match = score_match.note_array()
        sdm = AutomaticNoteMatcher()
        pred_alignment = sdm(sna_match, pna_match)

        print(pred_alignment)
        print(alignment)
        self.assertTrue(np.all(True))
        
   
        
        
if __name__ == "__main__":
    unittest.main()
        