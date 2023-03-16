#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This module contains full note matcher classes.
"""
import numpy as np
from scipy.interpolate import interp1d
from collections import defaultdict

import time
from itertools import combinations
from scipy.special import binom

from .dtw import DTW, element_of_metric
from .nwtw import NW_DTW, NW

from .preprocessors import (mend_note_alignments,
                            cut_note_arrays,
                            alignment_times_from_dtw,
                            note_per_ons_encoding)

################################### SYMBOLIC MATCHERS ###################################


class SimplestGreedyMatcher(object):
    """
    Create alignment in MAPS format (dict) by greedy pitch matching from performance and score note_array
    """
    def __call__(self, score_note_array, performance_note_array):
        alignment = []
        s_aligned = []
        p_aligned = []
        for s_note in score_note_array:
            sid = s_note['id']
            pid = None

            # filter performance notes with matching pitches
            matching_pitches = performance_note_array[s_note['pitch'] == performance_note_array['pitch']]

            for p_note in matching_pitches:
                # take first matching performance note that was not yet aligned
                if p_note not in p_aligned:
                    pid = str(p_note['id'])
                    p_aligned.append(p_note)
                    s_aligned.append(s_note)
                    break

            if pid is not None:
                alignment.append({'label': 'match', 'score_id': sid, 'performance_id': str(pid)})
            else:
                # if score note could not be aligned it counts as a deletion
                alignment.append({'label': 'deletion', 'score_id': sid})

        # check for unaligned performance notes (ie insertions)
        for p_note in performance_note_array:
            if p_note not in p_aligned:
                alignment.append({'label': 'insertion', 'performance_id': str(p_note['id'])})

        return alignment


class SequenceAugmentedGreedyMatcher(object):
    """
    Create alignment in MAPS format (dict) by sequence augmented pitch matching from performance and score note_array
    """
    def __init__(self):
        self.overlap = False

    def __call__(self, 
                 score_note_array, 
                 performance_note_array, 
                 alignment_times, 
                 shift=False, 
                 cap_combinations = 10000):
        alignment = []
        # s_aligned = []
        p_aligned = []

        # DTW gives non-unique times, sometimes...
        # TODO: safety net
        try:
            onset_time_conversion = interp1d(alignment_times[:, 0],
                                             alignment_times[:, 1],
                                             fill_value="extrapolate")
        except ValueError:
            if len(alignment_times) < 2:
                onset_time_conversion = \
                    lambda x: np.ones_like(x) * alignment_times[0, 1]  # noqa: E731

        score_pitches = np.unique(score_note_array["pitch"])
        # loop over pitches and align full sequences of matching pitches in correct order
        # if sequences mismatch in length, classify extra notes as insertions or deletions respectively
        for pitch in score_pitches:
         


            score_notes = score_note_array[pitch == score_note_array['pitch']]
            performance_notes = performance_note_array[pitch == performance_note_array['pitch']]
       
            score_notes_onsets = onset_time_conversion(score_notes["onset_beat"])
            score_notes_onsets_idx = np.argsort(score_notes_onsets)
            score_notes_onsets = score_notes_onsets[score_notes_onsets_idx]
    
            performance_notes_onsets = performance_notes["onset_sec"]
            performance_notes_onsets_idx = np.argsort(performance_notes_onsets)
            performance_notes_onsets = performance_notes_onsets[performance_notes_onsets_idx]

            score_no = score_notes_onsets.shape[0]
            performance_no = performance_notes_onsets.shape[0]
    
            common_no = min(score_no, performance_no)
            extra_no = max(score_no, performance_no)-common_no
            score_longer = np.argmax([performance_no, score_no])

            if score_longer:
                longt = score_notes_onsets
                shortt = performance_notes_onsets
                longid = score_notes_onsets_idx
                shortid = performance_notes_onsets_idx
            else:
                longt = performance_notes_onsets
                shortt = score_notes_onsets
                longid = performance_notes_onsets_idx
                shortid = score_notes_onsets_idx

            diffs = dict()
 
            if shift:
                if cap_combinations is not None:
                    combination_number = binom(max(score_no, performance_no), extra_no)
                    if combination_number > cap_combinations:
                        combs = [np.random.choice(max(score_no, performance_no), extra_no, replace=False) for n in range(cap_combinations)]  

                        print("high number of combinations: ", combination_number, "low number sampled ", len(combs))
                    else:
                        combs = combinations(range(max(score_no, performance_no)), extra_no)
                else:
                    combs = combinations(range(max(score_no, performance_no)), extra_no)
                for omit_idx in combinations(range(max(score_no, performance_no)), extra_no):
                    shortenedt = np.delete(longt,list(omit_idx))
                    optimal_shift = np.mean(shortenedt-shortt)
                    shift_diff = np.sum(np.abs(shortenedt-shortt-optimal_shift*np.ones_like(shortenedt))**2)
                    diffs[shift_diff] = list(omit_idx)


            else:
                
                if cap_combinations is not None:
                    combination_number = binom(max(score_no, performance_no), extra_no)
                    if combination_number > cap_combinations:
                        combs = [np.random.choice(max(score_no, performance_no), extra_no, replace=False) for n in range(cap_combinations)]  

                        print("high number of combinations: ", combination_number, "low number sampled ", len(combs))
                    else:
                        combs = combinations(range(max(score_no, performance_no)), extra_no)
                else:
                    combs = combinations(range(max(score_no, performance_no)), extra_no)
                for omit_idx in combs:

                    shortenedt = np.delete(longt,list(omit_idx))
                    diff = np.sum(np.abs(shortenedt-shortt)**2)
                    diffs[diff] = list(omit_idx)

            best_omit_dist = np.min(list(diffs.keys()))
            best_omit_idx = diffs[best_omit_dist]

            # get the arrays of actual onset times
            aligns = np.delete(longt, best_omit_idx)
            nonaligns = longt[best_omit_idx]
            # get the idx of the original note_arrays
            align_ids = np.delete(longid, best_omit_idx)
            nonalign_ids = longid[best_omit_idx]

            if score_longer:
                for sid, pid in zip(score_notes["id"][align_ids], performance_notes["id"][performance_notes_onsets_idx]):
                    alignment.append({'label': 'match', 'score_id': sid, 'performance_id': str(pid)})
                    p_aligned.append(str(pid))

                for sid in score_notes["id"][nonalign_ids]:
                    alignment.append({'label': 'deletion', 'score_id': sid})

            else:
                for sid, pid in zip(score_notes["id"][score_notes_onsets_idx], performance_notes["id"][align_ids]):
                    alignment.append({'label': 'match', 'score_id': sid, 'performance_id': str(pid)})
                    p_aligned.append(str(pid))

                for pid in performance_notes["id"][nonalign_ids]:
                    alignment.append({'label': 'insertion', 'performance_id': str(pid)})
                    p_aligned.append(str(pid))

        # check for unaligned performance notes (ie insertions)
        for p_note in performance_note_array:
            if str(p_note['id']) not in p_aligned:
                alignment.append({'label': 'insertion', 'performance_id': str(p_note['id'])})

        return alignment
    
    
class OnsetGreedyMatcher(object):
    """
    Create alignment in MAPS format (dict) 
    by pitch matching from an onset-wise
    alignment
    """
    def __call__(self, 
                 score_note_array, 
                 performance_note_array,
                 onset_alignment):
        alignment = []
        s_aligned = []
        p_aligned = []
        unique_onsets = np.unique(score_note_array['onset_beat'])
        # for p_no, p_note in enumerate(performance_note_array):
        for p_no, s_onset_no in onset_alignment:
            p_note = performance_note_array[p_no]
            pid = p_note['id']
            sid = None
            
            for k in range(2): # check onsets up to 5 steps in the future
                # s_candidate_mask = onset_alignment[p_no]
                try: 
                    s_onset = unique_onsets[s_onset_no+k]
                    score_note_array_segment = score_note_array[score_note_array['onset_beat'] == s_onset]
                    # filter performance notes with matching pitches
                    matching_pitches = score_note_array_segment[p_note['pitch'] == score_note_array_segment['pitch']]

                    for s_note in matching_pitches:
                        # take first matching performance note that was not yet aligned
                        if s_note not in s_aligned and p_note not in p_aligned:
                            sid = str(s_note['id'])
                            p_aligned.append(p_note)
                            s_aligned.append(s_note)
                            break 
                    
                    if sid is not None or len(matching_pitches) == 0:
                        break
                   
                except:
                    print("next onset trial error in OnsetGreedyMatcher")

            if sid is not None:
                alignment.append({'label': 'match', 'score_id': sid, 'performance_id': str(pid)})
                
        
        # check for unaligned performance notes (ie insertions) 
        for p_no, p_note in enumerate(performance_note_array):
            if p_note not in p_aligned:
                # neighborhood watch
                pid = p_note['id']
                mask  = (onset_alignment[:,0] == p_no)
                sid = None
                s_onset = np.min(unique_onsets[onset_alignment[mask,1]])
                smask  = np.all((score_note_array['onset_beat'] < s_onset + 4, score_note_array['onset_beat'] > s_onset - 4), axis= 0)
                possible_score_notes = score_note_array[smask]
                for s_note in possible_score_notes:
                    if s_note["pitch"] == p_note["pitch"] and s_note not in s_aligned:
                        sid = str(s_note['id'])
                        p_aligned.append(p_note)
                        s_aligned.append(s_note)
                        alignment.append({'label': 'match', 'score_id': sid, 'performance_id': str(pid)})
                        break
                
                # ok enough
                if sid is None:
                    alignment.append({'label': 'insertion', 'performance_id': str(p_note['id'])})
                
        # check for unaligned score notes (ie deletions)
        for s_note in score_note_array:
            if s_note not in s_aligned:           
                alignment.append({'label': 'deletion', 'score_id': str(s_note['id'])})
             
        return alignment


class CleanOnsetMatcher(object):
    """
    Create alignment in MAPS format (dict) 
    by pitch matching from an onset-wise
    alignment
    """
    def __call__(self, 
                 score_note_array, 
                 performance_note_array,
                 onset_alignment):


        # Get time alignments from first unaligned notes
        print("clean dtw alignment")
        s_aligned = []
        p_aligned = []
        time_tuples = defaultdict(list)
        unique_onsets = np.unique(score_note_array['onset_beat'])
        # for p_no, p_note in enumerate(performance_note_array):
        for p_no, s_onset_no in onset_alignment:
            p_note = performance_note_array[p_no]
            pid = str(p_note['id'])
            if pid not in p_aligned:
                s_onset = unique_onsets[s_onset_no]
                if s_onset_no > 0:
                    s_onset_prev = unique_onsets[s_onset_no-1]
                else: 
                    s_onset_prev = -10
                score_note_array_segment = score_note_array[score_note_array['onset_beat'] == s_onset]
                score_note_array_segment_prev = score_note_array[score_note_array['onset_beat'] == s_onset_prev]
                matching_pitches = score_note_array_segment[p_note['pitch'] == score_note_array_segment['pitch']]
            

                #
                # print(s_onset, matching_pitches.shape)
            
                for s_note in matching_pitches:
                    sid = str(s_note['id'])
                    # take first matching performance note that was not yet aligned
                    if sid not in s_aligned and s_note["pitch"] not in score_note_array_segment_prev["pitch"]:
                        p_aligned.append(pid)
                        s_aligned.append(sid)
                        time_tuples[s_note["onset_beat"]].append( p_note["onset_sec"])
                        break 
        
        x_score = list()
        y_perf = list()
        for k in time_tuples.keys():
            x_score.append(k)
            y_perf.append(np.min(time_tuples[k]))

        score_to_perf_map = interp1d(x_score,
                                     y_perf,
                                     fill_value="extrapolate")

        x_score_cut_locations = np.array(x_score + [x_score[-1]+10]) - 0.05

        cleaned_alignment = np.column_stack((x_score_cut_locations, score_to_perf_map(x_score_cut_locations)))
        
        print("cut note arrays", cleaned_alignment.shape)

        score_note_arrays, performance_note_arrays = cut_note_arrays(performance_note_array, 
                    score_note_array, 
                    cleaned_alignment,
                    sfuzziness=0.0, 
                    pfuzziness=0.0, 
                    window_size=1,
                    pfuzziness_relative_to_tempo=False)

        symbolic_note_matcher=SequenceAugmentedGreedyMatcher()
        note_alignments = list()

        print("local alignment", len(score_note_arrays))

        for window_id in range(len(score_note_arrays)):
            dtw_alignment_times = cleaned_alignment[window_id:window_id+2, :]
            fine_local_alignment = symbolic_note_matcher(
                    score_note_arrays[window_id],
                    performance_note_arrays[window_id],
                    dtw_alignment_times,
                    shift=False,
                    cap_combinations=100)

            note_alignments.append(fine_local_alignment)

        print("global alignment")

        # MEND windows to global alignment
        global_alignment, score_alignment, \
            performance_alignment = mend_note_alignments(note_alignments, 
                                                    performance_note_array,
                                                    score_note_array, 
                                                    node_times=cleaned_alignment,
                                                    symbolic_note_matcher= symbolic_note_matcher,
                                                    max_traversal_depth=1500)

        return global_alignment


################################### FULL MODEL MATCHERS ###################################


class PianoRollSequentialMatcher(object):
    def __init__(self,
                 note_matcher=DTW,
                 matcher_kwargs=dict(metric="euclidean"),
                 node_cutter=cut_note_arrays,
                 node_mender=mend_note_alignments,
                 symbolic_note_matcher=SequenceAugmentedGreedyMatcher(),
                 greedy_symbolic_note_matcher=SimplestGreedyMatcher(),
                 alignment_type="dtw",
                 SCORE_FINE_NODE_LENGTH=0.25,
                 s_time_div=16,
                 p_time_div=16,
                 sfuzziness=0.5,
                 pfuzziness=0.5,
                 window_size=1,
                 pfuzziness_relative_to_tempo=True,
                 shift_onsets=False,
                 cap_combinations=None):

        self.note_matcher = note_matcher(**matcher_kwargs)
        self.symbolic_note_matcher = symbolic_note_matcher
        self.node_cutter = node_cutter
        self.node_mender = node_mender
        self.greedy_symbolic_note_matcher = greedy_symbolic_note_matcher
        self.alignment_type = alignment_type
        self.SCORE_FINE_NODE_LENGTH = SCORE_FINE_NODE_LENGTH
        self.s_time_div = s_time_div
        self.p_time_div = p_time_div
        self.sfuzziness = sfuzziness
        self.pfuzziness = pfuzziness
        self.window_size = window_size
        self.pfuzziness_relative_to_tempo = pfuzziness_relative_to_tempo
        self.shift_onsets = shift_onsets
        self.cap_combinations = cap_combinations

    def __call__(self, score_note_array,
                 performance_note_array, 
                 alignment_times):
        
        # cut arrays to windows
        score_note_arrays, performance_note_arrays = self.node_cutter(
            performance_note_array,
            score_note_array,
            np.array(alignment_times),
            sfuzziness=self.sfuzziness, 
            pfuzziness=self.pfuzziness,
            window_size=self.window_size,
            pfuzziness_relative_to_tempo=self.pfuzziness_relative_to_tempo)

        # compute windowed alignments
        note_alignments = []
        dtw_al = []

        for window_id in range(len(score_note_arrays)):  
            if self.alignment_type == "greedy":
                alignment = self.greedy_symbolic_note_matcher(
                    score_note_arrays[window_id],
                    performance_note_arrays[window_id])
                note_alignments.append(alignment)
            else:
                # _____________ fine alignment ____________
                if self.alignment_type == "dtw":
                    if score_note_arrays[window_id].shape[0] == 0 or \
                        performance_note_arrays[window_id].shape[0] == 0:
                        # for empty arrays fall back to linear
                        dtw_alignment_times = np.array(alignment_times)[
                                window_id:window_id+2, :]

                    else:    
                        dtw_alignment_times = alignment_times_from_dtw(
                            score_note_arrays[window_id],
                            performance_note_arrays[window_id],
                            matcher=self.note_matcher,
                            SCORE_FINE_NODE_LENGTH=self.SCORE_FINE_NODE_LENGTH,
                            s_time_div=self.s_time_div,
                            p_time_div=self.p_time_div)
                else:
                    dtw_alignment_times = np.array(alignment_times)[
                        window_id:window_id+2, :]

                dtw_al.append(dtw_alignment_times)
               
                # distance augmented greedy align
                fine_local_alignment = self.symbolic_note_matcher(
                    score_note_arrays[window_id],
                    performance_note_arrays[window_id],
                    dtw_alignment_times,
                    shift=self.shift_onsets,
                    cap_combinations=self.cap_combinations)

                note_alignments.append(fine_local_alignment)

                

        # MEND windows to global alignment
        global_alignment, score_alignment, \
            performance_alignment = self.node_mender(note_alignments, 
                                                    performance_note_array,
                                                    score_note_array, 
                                                    node_times=np.array(alignment_times),
                                                    symbolic_note_matcher= self.symbolic_note_matcher,
                                                    max_traversal_depth=1500)

        return global_alignment


class PianoRollNoNodeMatcher(object):
    def __init__(self,
                 note_matcher=DTW,
                 matcher_kwargs=dict(metric="cosine"),#"euclidean"),
                 node_cutter=cut_note_arrays,
                 node_mender=mend_note_alignments,
                 symbolic_note_matcher=SequenceAugmentedGreedyMatcher(),
                 greedy_symbolic_note_matcher=SimplestGreedyMatcher(),
                 alignment_type="dtw",
                 SCORE_FINE_NODE_LENGTH=0.25,
                 s_time_div=16,
                 p_time_div=16,
                 sfuzziness=4.0,#0.5,
                 pfuzziness=4.0,#0.5,
                 window_size=1,
                 pfuzziness_relative_to_tempo=True,
                 shift_onsets=False,
                 cap_combinations=None):

        self.note_matcher = note_matcher(**matcher_kwargs)
        self.symbolic_note_matcher = symbolic_note_matcher
        self.node_cutter = node_cutter
        self.node_mender = node_mender
        self.greedy_symbolic_note_matcher = greedy_symbolic_note_matcher
        self.alignment_type = alignment_type
        self.SCORE_FINE_NODE_LENGTH = SCORE_FINE_NODE_LENGTH
        self.s_time_div = s_time_div
        self.p_time_div = p_time_div
        self.sfuzziness = sfuzziness
        self.pfuzziness = pfuzziness
        self.window_size = window_size
        self.pfuzziness_relative_to_tempo = pfuzziness_relative_to_tempo
        self.shift_onsets = shift_onsets
        self.cap_combinations = cap_combinations

    def __call__(self, score_note_array,
                 performance_note_array,
                 verbose_time=False):
        
        t1 = time.time()
        # start with DTW
        dtw_alignment_times_init = alignment_times_from_dtw(
                            score_note_array,
                            performance_note_array,
                            matcher=self.note_matcher,
                            SCORE_FINE_NODE_LENGTH=4.0,
                            s_time_div=self.s_time_div,
                            p_time_div=self.p_time_div
                            )
        # cut arrays to windows
        t11 = time.time()
        if verbose_time:
            print(format(t11-t1, ".3f"), "sec : Initial coarse DTW pass")
        score_note_arrays, performance_note_arrays = self.node_cutter(
            performance_note_array,
            score_note_array,
            np.array(dtw_alignment_times_init),
            sfuzziness=self.sfuzziness, 
            pfuzziness=self.pfuzziness,
            window_size=self.window_size,
            pfuzziness_relative_to_tempo=self.pfuzziness_relative_to_tempo)

        # compute windowed alignments
        note_alignments = []
        dtw_al = []

        t2 = time.time()
        if verbose_time:
            print(format(t2-t11, ".3f"), "sec : Cutting")
            
        for window_id in range(len(score_note_arrays)):
            if self.alignment_type == "greedy":
                alignment = self.greedy_symbolic_note_matcher(
                    score_note_arrays[window_id],
                    performance_note_arrays[window_id])
                note_alignments.append(alignment)
            else:
                # _____________ fine alignment ____________
                if self.alignment_type == "dtw":
                    if score_note_arrays[window_id].shape[0] == 0 or \
                        performance_note_arrays[window_id].shape[0] == 0:
                        # for empty arrays fall back to linear
                        dtw_alignment_times = np.array(dtw_alignment_times_init)[
                                window_id:window_id+2, :]

                    else:    
                        dtw_alignment_times = alignment_times_from_dtw(
                            score_note_arrays[window_id],
                            performance_note_arrays[window_id],
                            matcher=self.note_matcher,
                            SCORE_FINE_NODE_LENGTH=self.SCORE_FINE_NODE_LENGTH,
                            s_time_div=self.s_time_div,
                            p_time_div=self.p_time_div)
                else:
                    dtw_alignment_times = np.array(dtw_alignment_times_init)[
                        window_id:window_id+2, :]

                dtw_al.append(dtw_alignment_times)
                
                # distance augmented greedy align
                fine_local_alignment = self.symbolic_note_matcher(
                    score_note_arrays[window_id],
                    performance_note_arrays[window_id],
                    dtw_alignment_times,
                    shift=self.shift_onsets,
                    cap_combinations=self.cap_combinations)

                note_alignments.append(fine_local_alignment)
        t41 = time.time()
        if verbose_time:
            print(format(t41-t2, ".3f"), "sec : Fine-grained DTW passes, symbolic matching")

        
        # MEND windows to global alignment
        global_alignment, score_alignment, \
            performance_alignment = self.node_mender(note_alignments, 
                                                    performance_note_array,
                                                    score_note_array, 
                                                    node_times=np.array(dtw_alignment_times_init),
                                                    symbolic_note_matcher= self.symbolic_note_matcher,
                                                    max_traversal_depth=150)
        t5 = time.time()
        if verbose_time:
            print(format(t5-t41, ".3f"), "sec : Mending")

        return global_alignment

# alias
AutomaticNoteMatcher = PianoRollNoNodeMatcher

# alias
AnchorPointNoteMatcher = PianoRollSequentialMatcher


class ChordEncodingMatcher(object):
    def __init__(self,
                 note_matcher=DTW,
                 matcher_kwargs=dict(metric=element_of_metric,
                                     cdist_local=True),
                 symbolic_note_matcher=OnsetGreedyMatcher(),
                 dtw_window_size=6):

        self.note_matcher = note_matcher(**matcher_kwargs)
        self.symbolic_note_matcher = symbolic_note_matcher
        self.dtw_window_size = dtw_window_size

    def __call__(self, score_note_array,
                 performance_note_array):
        
        # create encodings
        score_note_per_ons_encoding = note_per_ons_encoding(score_note_array)
        
        # match by onset
        matcher = DTW(metric = element_of_metric, cdist_local = True)
        
        _, onset_alignment_path = matcher(performance_note_array["pitch"], 
                                          score_note_per_ons_encoding,  return_path=True)


        # match by note
        global_alignment = self.symbolic_note_matcher(
                                                    score_note_array, 
                                                    performance_note_array,
                                                    onset_alignment_path
                                                    )
                                                
        return global_alignment, onset_alignment_path