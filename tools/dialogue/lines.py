# SPDX-License-Identifier: Apache-2.0
"""SPECIAL OPS dialogue: every voiced line in the game.

Original writing for this project. Each line is (id, speaker, text, emotion). The emotion drives
the face (neutral, smile, concern, focus, surprise, deadpan) and may be omitted. Speaker keys
are in VOICES. tools/audio/build_voices.py renders each line offline to
assets/audio/voice/<id>.ogg and writes scripts/lib/voice_data.luau with timing and lip data.

Cast (continued below)
  Voss      Greyline's site lead; tired, polite, paid by the day
  Site PA   the Vellwood facility's automated announcement voice
Cast
  Rook      the player; a new transfer to Halyard Team (mostly silent, the squad talks to you)
  Anchor    team lead; dry, steady, has done this too long
  Patch     medic and field tech; warm, practical, teases Anchor
  Echo      scout; quiet, precise, notices everything
  Tally     comms and heavy kit; talkative, superstitious about paperwork
  Lamplight mission control on the radio
  Hollis    a forest ranger who stayed behind
  Greyline  contractors hired to "recover Asset V-01"
"""

# speaker -> (Kokoro voice id, speed, radio filter, subtitle name)
VOICES = {
    "anchor": ("bm_george", 0.95, False, "ANCHOR"),
    "patch": ("af_sarah", 1.0, False, "PATCH"),
    "echo": ("af_nicole", 1.0, False, "ECHO"),
    "tally": ("am_puck", 1.05, False, "TALLY"),
    "rook": ("am_michael", 1.0, False, "ROOK"),
    "lamplight": ("bf_isabella", 1.0, True, "LAMPLIGHT"),
    "hollis": ("bm_lewis", 0.92, False, "HOLLIS"),
    "greyline1": ("am_onyx", 1.0, True, "GREYLINE"),
    "greyline2": ("am_eric", 1.05, True, "GREYLINE"),
    "voss_radio": ("bm_daniel", 0.97, True, "VOSS"),
    "voss": ("bm_daniel", 0.97, False, "VOSS"),
    "pa": ("bf_alice", 0.9, True, "SITE PA"),
}

LINES = [
    # ---- Prologue: briefing in the staging truck, deployment -----------------------------------
    ("pro_01", "lamplight", "Halyard Team, this is Lamplight. Confirm you have the new transfer.", "neutral"),
    ("pro_02", "anchor", "We have them. Rook's sitting on my good crate.", "deadpan"),
    ("pro_03", "patch", "It's your only crate, Anchor.", "smile"),
    ("pro_04", "lamplight", "Brief is short. The Vellwood research site went quiet nine days ago. No alarms, no calls. Just quiet.", "neutral"),
    ("pro_05", "lamplight", "A contractor outfit called Greyline has been hired to recover something the paperwork calls Asset V-01.", "concern"),
    ("pro_06", "tally", "Asset V-01. Nobody puts a number on a thing unless there's more than one of it.", "concern"),
    ("pro_07", "echo", "Or unless they lost the first one.", "deadpan"),
    ("pro_08", "lamplight", "You get there first, you find out what V-01 is, and you keep it out of Greyline's hands. Pulse rounds only. Nobody gets hurt.", "focus"),
    ("pro_09", "anchor", "Understood. Rook, you're with me. Echo takes point, Patch keeps us upright, Tally keeps us talking.", "focus"),
    ("pro_10", "tally", "I always keep us talking.", "smile"),
    ("pro_11", "patch", "That's the problem.", "smile"),
    ("pro_12", "anchor", "Vehicle stops at the old ranger road. We walk from there. Check your kit.", "neutral"),

    # ---- Operation 01: Vellwood forest ------------------------------------------------------------
    ("op1_arrive_01", "echo", "Trail's clear for the first stretch. Fresh boot prints, though. Heavy soles.", "focus"),
    ("op1_arrive_02", "anchor", "Greyline. They beat us to the road.", "concern"),
    ("op1_arrive_03", "tally", "Lamplight said nine days. Those prints are from this morning.", "concern"),
    ("op1_arrive_04", "anchor", "Then we move quietly. Rook, stay close and keep your eyes up.", "focus"),
    ("op1_trail_01", "patch", "Mind the roots. I'm not carrying anyone out of here on day one.", "smile"),
    ("op1_trail_02", "echo", "Marker post ahead. Someone's scratched the arrows off it.", "focus"),
    ("op1_marker_01", "echo", "Ranger markers point to a cabin east of the creek. Somebody didn't want that found.", "focus"),
    ("op1_marker_02", "anchor", "Good eye. We check the cabin.", "neutral"),
    ("op1_cabin_01", "hollis", "That's far enough. Hands where I can see them. Oh. You're not grey.", "surprise"),
    ("op1_cabin_02", "anchor", "Halyard Team. We're here about the research site.", "neutral"),
    ("op1_cabin_03", "hollis", "Hollis. Ranger. Only one left. The others went down the mountain when the lights went off up there.", "concern"),
    ("op1_cabin_04", "patch", "You've been out here alone for nine days?", "concern"),
    ("op1_cabin_05", "hollis", "Eight. I counted the first one twice. Those Greyline people put a sensor relay on the north ridge. It sees everything on the trail.", "deadpan"),
    ("op1_cabin_06", "tally", "A relay I can talk to. Get me close and I'll make it see trees.", "smile"),
    ("op1_cabin_07", "hollis", "Take the creek path. And if you find what they're looking for, tell me it's worth all this.", "neutral"),
    ("op1_patrol_01", "echo", "Contact. Two Greyline, by the fallen pines. They haven't seen us.", "focus"),
    ("op1_patrol_02", "anchor", "Rook, your call. Take them when you're ready, we'll follow your lead.", "focus"),
    ("op1_patrol_03", "tally", "That was tidy. They'll wake up with a headache and a story.", "smile"),
    ("op1_relay_01", "tally", "There's the relay. Rook, scan it, then pull the cell. I'll handle the rest.", "focus"),
    ("op1_relay_02", "tally", "And it's blind. Lamplight, the north ridge relay is ours.", "smile"),
    ("op1_relay_03", "lamplight", "Copy, Halyard. Greyline will notice. Expect company at the clearing.", "concern"),
    ("op1_ambush_01", "anchor", "Here they come. Spread out, find cover.", "focus"),
    ("op1_ambush_02", "patch", "I've got your back, Rook. Keep moving, don't stand in the open.", "focus"),
    ("op1_ambush_03", "echo", "Last one's down. Clearing's quiet.", "neutral"),
    ("op1_ridge_01", "echo", "Fence line through the trees. That's the perimeter.", "focus"),
    ("op1_ridge_02", "anchor", "Take a breath. Everybody good?", "neutral"),
    ("op1_ridge_03", "tally", "Good. Muddy. Mostly good.", "smile"),
    ("op1_ridge_04", "patch", "Rook did well. Don't tell them, it'll go to their head.", "smile"),
    ("op1_ridge_05", "anchor", "Lamplight, Halyard. Forest is clear. Moving to the perimeter.", "neutral"),
    ("op1_ridge_06", "lamplight", "Copy, Halyard. Good work. Lamplight out.", "neutral"),

    # ---- Prologue: the drive in the Mule (Anchor drives, Rook in the middle rear seat) ----------
    ("ride_01", "tally", "Rook, rule one of the Mule. Don't touch the blue switch.", "neutral"),
    ("ride_02", "patch", "What does the blue switch do?", "neutral"),
    ("ride_03", "tally", "Nobody knows. That's why it's rule one.", "deadpan"),
    ("ride_04", "echo", "Road's washed out past the culvert. Stay left, Anchor.", "focus"),
    ("ride_05", "anchor", "I've driven this road before, Echo.", "deadpan"),
    ("ride_06", "echo", "You drove it into the ditch before.", "deadpan"),
    ("ride_07", "patch", "He did. I have the photographs.", "smile"),
    ("ride_08", "anchor", "Two minutes. Helmets on, chatter off.", "neutral"),
    ("ride_09", "anchor", "Everybody out. Echo, take point.", "neutral"),

    # ---- Operation 02: perimeter ------------------------------------------------------------------
    ("op2_01", "echo", "Three towers on the fence. One guard each, maybe two on the gate.", "focus"),
    ("op2_02", "tally", "The gate booth runs the fence. Get me to that panel and I can open it.", "focus"),
    ("op2_03", "anchor", "Towers first. If they look down at the wrong moment, we lose the quiet.", "focus"),
    ("op2_04", "patch", "Pulse rounds carry. Pick your shots, Rook.", "concern"),
    ("op2_05", "echo", "Towers are clear. Nobody saw a thing.", "neutral"),
    ("op2_06", "anchor", "Gate booth. Rook, get Tally to the panel.", "focus"),
    ("op2_07", "tally", "Panel's on. It wants a password. It always wants a password.", "focus"),
    ("op2_08", "tally", "Give me thirty seconds. Keep anyone off my back.", "focus"),
    ("op2_09", "voss_radio", "Gate booth, this is Voss. Your fence just told me it's having a birthday. Explain.", "deadpan"),
    ("op2_10", "echo", "Truck on the service road. They're sending a team.", "focus"),
    ("op2_11", "tally", "Got it. The password was password. I'm not even proud.", "smile"),
    ("op2_12", "anchor", "Gate's open. Through, and into the yard.", "neutral"),

    # ---- Operation 03: facility approach (service yard) -----------------------------------------
    ("op3_01", "lamplight", "Halyard, the facility entrance needs a site access card. Try the office in the yard.", "neutral"),
    ("op3_02", "anchor", "Yard's patrolled. Clear it, then search the office.", "focus"),
    ("op3_03", "patch", "Garage on the left, office ahead. Watch the containers, they make good corners.", "focus"),
    ("op3_04", "echo", "Yard is quiet.", "neutral"),
    ("op3_05", "tally", "There's a card on the desk with a sticky note. Do not lose this card. Underlined twice.", "smile"),
    ("op3_06", "anchor", "Someone lost it anyway. Good. Rook, take it to the entrance.", "neutral"),
    ("op3_07", "voss_radio", "Halyard Team, I assume. Voss, Greyline. We are both paid to be here, so let's not make this personal.", "neutral"),
    ("op3_08", "anchor", "Nobody's getting hurt today, Voss. That's the only personal part.", "focus"),
    ("op3_09", "voss_radio", "Agreed. Pulse rounds only. My people bruise easily and bill accordingly.", "deadpan"),
    ("op3_10", "tally", "I like him. I don't trust him, but I like him.", "smile"),

    # ---- Operation 04: facility interior ---------------------------------------------------------
    ("op4_01", "pa", "Welcome to the Vellwood Research Site. Please remember to sign the visitor log.", "neutral"),
    ("op4_02", "tally", "I'm signing it. Somebody has to.", "neutral"),
    ("op4_03", "patch", "Coffee cups on every desk. They left in a hurry.", "concern"),
    ("op4_04", "echo", "Or they left on a Friday.", "deadpan"),
    ("op4_05", "lamplight", "Halyard, your signal is degrading. Main power is out. Find the switch room before you go deeper.", "concern"),
    ("op4_06", "anchor", "Switch room's on the plan. Second corridor, past the labs.", "focus"),
    ("op4_07", "tally", "Breakers. Somebody labelled every one of them. I could cry.", "smile"),
    ("op4_08", "pa", "Power restored. Thank you for your patience.", "neutral"),
    ("op4_09", "echo", "Greyline, in the labs. They heard the lights come on.", "focus"),
    ("op4_10", "anchor", "Clear the labs. Then the lift to the bunker.", "focus"),

    # ---- Operation 05: bunker ---------------------------------------------------------------------
    ("op5_01", "patch", "Lift goes down a long way for a building that grows lettuce.", "concern"),
    ("op5_02", "tally", "The sign upstairs said soil science. The lift says level minus four.", "neutral"),
    ("op5_03", "echo", "Blast door. Manual crank. Greyline left it half open.", "focus"),
    ("op5_04", "anchor", "Rook, work the crank. We'll cover.", "focus"),
    ("op5_05", "voss_radio", "You're in the bunker. You'll find my second team there. Please be gentle, it's their first week.", "deadpan"),
    ("op5_06", "patch", "Is anybody else worried about how polite this man is?", "concern"),
    ("op5_07", "echo", "Bunker's clear. Stairs going down again.", "neutral"),

    # ---- Operation 06: lower basement -------------------------------------------------------------
    ("op6_01", "tally", "Archive. Thousands of boxes. Every one says V something.", "surprise"),
    ("op6_02", "echo", "V-01 is in the chamber at the far end. The chamber key is on a manager's ring.", "focus"),
    ("op6_03", "anchor", "Then we find the manager's office. Spread out, stay in sight of each other.", "focus"),
    ("op6_04", "patch", "Pump room on the left. Mind the wet floor.", "concern"),
    ("op6_05", "tally", "Key ring. Forty keys. One of them has a smiley face on it.", "smile"),
    ("op6_06", "echo", "That's the one.", "deadpan"),
    ("op6_07", "voss_radio", "Halyard, I've got my last four people at the chamber. Let's not do this. Let's do it a bit, if we must.", "neutral"),
    ("op6_08", "anchor", "Last push. On me.", "focus"),

    # ---- Operation 07: the chamber and V-01 ------------------------------------------------------
    ("op7_01", "voss", "All right. All right. Nobody shoot. I'm putting it down. That's my lunch, actually.", "concern"),
    ("op7_02", "anchor", "Voss. Who hired you?", "focus"),
    ("op7_03", "voss", "Vellwood's finance office. They're closing the site and they're missing one asset off the inventory.", "deadpan"),
    ("op7_04", "tally", "Nine days. Two private armies. For an inventory?", "surprise"),
    ("op7_05", "voss", "It's a very strict auditor.", "deadpan"),
    ("op7_06", "echo", "There's something behind the chair.", "focus"),
    ("op7_07", "patch", "Rook, careful. Slowly.", "concern"),
    ("op7_08", "tally", "That's a dummy. A test dummy. With a label on its foot that says V-01.", "surprise"),
    ("op7_09", "echo", "Vellwood seating trial, unit one. It tests chairs.", "deadpan"),
    ("op7_10", "patch", "So the asset is a man for sitting on chairs.", "smile"),
    ("op7_11", "anchor", "Lamplight, Halyard. We have V-01. It's a chair-testing dummy. Over.", "deadpan"),
    ("op7_12", "lamplight", "Say again, Halyard.", "surprise"),
    ("op7_13", "anchor", "A dummy, Lamplight. Very well made. Excellent posture.", "deadpan"),
    ("op7_14", "lamplight", "Copy. Bring it home. Finance would like it signed for.", "neutral"),
    ("op7_15", "tally", "I have the form. I have three copies of the form.", "smile"),
    ("op7_16", "voss", "Can I at least have a photo with it? For the invoice.", "smile"),

    # ---- Ending ----------------------------------------------------------------------------------
    ("end_01", "hollis", "That's it? That's what all this was?", "surprise"),
    ("end_02", "patch", "He's got very good posture, Hollis.", "smile"),
    ("end_03", "hollis", "Huh. Nine days. I'm going to go and sit down.", "deadpan"),
    ("end_04", "echo", "Not on that chair.", "deadpan"),
    ("end_05", "anchor", "Load up, Halyard. Rook, you did good. Welcome to the team.", "smile"),
    ("end_06", "tally", "Middle seat again, Rook. Don't touch the blue switch.", "smile"),

    # ---- Ambient squad chatter (operators talking to each other) --------------------------------
    ("chat_01a", "tally", "Patch, what do you think V-01 is? Honestly.", "neutral"),
    ("chat_01b", "patch", "Honestly? Something expensive somebody forgot to return.", "smile"),
    ("chat_01c", "echo", "Things get very expensive when nobody knows what they are.", "deadpan"),
    ("chat_02a", "anchor", "Tally, you filed the mission form?", "neutral"),
    ("chat_02b", "tally", "Twice. In pencil, and in pen. You can't be too careful.", "smile"),
    ("chat_02c", "anchor", "One of these days I'll ask why.", "deadpan"),
    ("chat_03a", "echo", "Birds stopped about a kilometre back.", "focus"),
    ("chat_03b", "patch", "Maybe they heard Tally.", "smile"),
    ("chat_03c", "tally", "Birds love me. Statistically.", "smile"),
    ("chat_04a", "patch", "Rook, if your boots are rubbing, tell me now, not in three hours.", "concern"),
    ("chat_04b", "anchor", "Listen to her. I didn't, once. Once.", "deadpan"),

    # ---- Combat barks (several variants each so they rotate) ------------------------------------
    ("bark_contact_1", "echo", "Contact front.", "focus"),
    ("bark_contact_2", "anchor", "Hostiles. Take cover.", "focus"),
    ("bark_contact_3", "tally", "Greyline, eyes up!", "focus"),
    ("bark_down_1", "patch", "That one's out.", "neutral"),
    ("bark_down_2", "echo", "Target down.", "neutral"),
    ("bark_down_3", "anchor", "Good hit.", "neutral"),
    ("bark_down_4", "tally", "Night night.", "smile"),
    ("bark_reload_1", "tally", "Changing cells.", "focus"),
    ("bark_reload_2", "echo", "Reloading.", "focus"),
    ("bark_clear_1", "anchor", "Area clear. Regroup on me.", "neutral"),
    ("bark_clear_2", "echo", "All quiet.", "neutral"),
    ("bark_hurt_1", "patch", "Rook, you're hit. Get behind something and breathe.", "concern"),
    ("bark_hurt_2", "patch", "Stay down a second, the shakes pass.", "concern"),
    ("bark_regroup_1", "anchor", "On me, Halyard.", "neutral"),
    ("bark_follow_1", "echo", "Following.", "neutral"),
    ("bark_hold_1", "anchor", "Holding here.", "neutral"),
    ("bark_wait_1", "tally", "Whenever you're ready, Rook.", "smile"),
    ("grey_contact_1", "greyline1", "Movement in the trees! Light them up!", "focus"),
    ("grey_contact_2", "greyline2", "We've got company. Stun pulses, don't let them close.", "focus"),
    ("grey_search_1", "greyline1", "Lost them. Spread out and sweep.", "concern"),
    ("grey_down_1", "greyline2", "Man down! He's just stunned, keep firing!", "surprise"),
    ("grey_idle_1", "greyline1", "Nine days for one asset. This had better be a big asset.", "deadpan"),
    ("grey_idle_2", "greyline2", "Contract says recover V-01 intact. Doesn't say what it is.", "deadpan"),
]
