# SPDX-License-Identifier: Apache-2.0
"""Voice casting and delivery direction for the human-performance voice pass (voice pass v3).

tools/dialogue/lines.py stays the single source of the words, speakers, subtitles and emotions.
This file only says WHO performs each speaker and, for selected lines, HOW: a delivery script
with inline performance tags (only the documented point-in-time events <sigh>, <laugh>, <short pause>;
written disfluencies such as "uh" are fine) that the speech model performs
but the subtitles never show. Lines without an entry are performed from their subtitle text.

Casting (Gemini 3.8 Flash TTS prebuilt voices; rendered offline at authoring time, only the
edited audio ships, no runtime TTS). One voice per character across every take; the radio,
recording and PA variants of a character reuse that character's voice so identity is continuous.
"""

CAST = {
    # squad
    "anchor": "charon",        # low, calm, steady: the dry, exhausted team lead
    "patch": "kore",           # firm, direct: the practical medic
    "echo": "aoede",           # relaxed, natural, understated scout
    "tally": "puck",           # quick, lively, easily startled comms man
    "brick": "algenib",        # low and gravelly: the big quiet breacher
    "brick_radio": "algenib",
    "rook": "iapetus",         # the player is silent; kept for completeness
    # support and opposition
    "lamplight": "erinome",    # clear, articulate HQ handler
    "hollis": "achird",        # friendly local ranger
    "venn": "sadaltager",      # learned, tired auditor
    "venn_rec": "sadaltager",
    "venn_radio": "sadaltager",
    "sorn": "orus",            # calm, firm field commander
    "sorn_radio": "orus",
    "sorn_pa": "orus",
    "kade": "algieba",         # smooth bureaucrat on his own recordings
    "greyline1": "alnilam",    # confident contractor
    "greyline2": "zubenelgenubi",  # casual, grumbling contractor
    "pa": "gacrux",            # mature, steady station announcement voice
}

# line id -> delivery script (same words as the subtitle, plus performance tags / punctuation).
# Keep the words identical to the subtitle so lip timing and captions agree.
DELIVERY = {
    "pro_08": "Understood. <short pause> Rook, you're with me. Echo on point... Patch keeps us upright... Tally keeps us connected. Brick went ahead an hour ago to clear the washout.",
    "pro_11": "<sigh> One rule, Rook. We bring back the person, and the proof. <short pause> We do not make a bad border worse.",
    "ride_05": "<sigh> I've driven this road before, Echo.",
    "op6_fan_01": "Something... is breathing.",
    # ASR review fixes (faster-whisper small.en): words that were swallowed or misheard
    "con_hurt_tally_1": "Tally. Yeah. Stung, but I'm up.",
    "con_up_tally_1": "Tally. Up. Radio's fine.",
    "op7_sorn_05": "He's stunned, not hurt. <short pause> Cuff him. Gently.",
    "op2_sign_05": "I was checking the fence line... For the record.",
    "op4_rec_07": "Or... it sat itself.",
    "op6_vault_01": "Original Northline source records. Raw logs, timestamps... They don't match a word of the public account.",
}
