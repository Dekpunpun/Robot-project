"""The case. Everything the game knows about the scenario lives here.

Four suspects instead of one, each cracking under a different mechanic (see
each suspect's "break" dict): Thorne needs a pile of evidence, Doss and
Ashworth need one specific piece of evidence *plus* the right question, and
Bricker needs no evidence at all — only for the detective to have explained,
in conversation, what is actually at stake.
"""

CASE = {
    "id": "the-vesper-manifest",
    "title": "The Vesper Manifest",
    "meta": {
        "title_lines": ("THE VESPER", "MANIFEST"),
        "subtitle": "A CITY ON THE CLOCK",
        "opening": (
            "00:12. Five VSP-5 demolition charges are missing from the Special "
            "Weapons vault at Fort Callow - together, enough to level a city "
            "block. No ransom note. No group has claimed them. You have until "
            "someone else's deadline to find out who took them, why, and where "
            "they are - though nobody has told you that part yet. Third "
            "Precinct is yours to leave whenever you're ready."
        ),
        "spawn": (32, 47),
    },
    "victim": {
        "name": "Mira Thorne",
        "detail": "31. Wife of Staff Sgt. Elias Thorne. Taken four days before the first theft.",
    },
    "scene": (
        "Fort Callow Special Weapons Vault, Harrow's Reach. A surprise ordnance audit this "
        "morning turned up five missing VSP-5 'Vesper' demolition charges - man-portable, "
        "built to drop a reinforced bridge span in a single blast, and together enough to "
        "level several city blocks. No forced entry. The vault's two-signature rule was "
        "satisfied on every checkout. Nothing on the surface points at anyone."
    ),
    "timeline": [
        ("-12d", "Mira Thorne is taken by the Cinder Compact. No one reports it yet."),
        ("-12n", "First of five vault checkouts begins, spread over twelve nights."),
        ("06:40", "The duty officer's incident report is filed, off an anonymous tip."),
        ("00:12", "Tonight. The deadline nobody has told the detective about yet."),
    ],
    "facts": [
        "Five VSP-5 cases are missing from Fort Callow's Special Weapons vault.",
        "The vault requires two-person sign-off; no one badge alone can check out a case.",
        "Vesper charges are inert without a separate detonator train, which is fully accounted for.",
        "The motor pool gate camera logs every vehicle in and out, timestamped, for the past week.",
        "A group calling itself the Cinder Compact is tied to two prior small bombings nearby.",
        "The audit was ordered off the back of an anonymous tip called in overnight.",
    ],
    "suspects": [
        {
            "id": "thorne",
            "name": "Staff Sergeant Elias Thorne",
            "sprite": "thorne",
            "role": "Special Weapons vault rotation, Fort Callow",
            "personality": (
                "Not hardened, not defiant - exhausted past the point of fear, holding on to "
                "one plan that has narrowed to a single option. Protective of Mira above "
                "literally everything else, including himself. Flat and quiet; answers get "
                "shorter the closer they get to her name."
            ),
            "publicAlibi": (
                "He says nothing is wrong. He hasn't slept, that's all. He was never home to "
                "ask because he's been at the vault, on the road, or here. He wants the "
                "detective to leave before it gets late."
            ),
            "hiddenTruth": (
                "He stole all five VSP-5 cases from the vault over twelve nights, using Colonel "
                "Ashworth's long-dormant override code to satisfy the two-signature rule without "
                "her knowledge, because the Cinder Compact took Mira four days before the first "
                "theft and has been issuing instructions since: one case at a time, or she "
                "doesn't come home. He drove each case home after hours and handed it off at a "
                "rotating roadside meeting point. Four are already gone. The fifth is with him "
                "now, at the family's fishing cabin on Salt Row, due at midnight."
            ),
            "motive": (
                "Not greed - Mira. He is paying a ransom in stolen ordnance because it's the "
                "only currency the Cinder Compact would take."
            ),
            "protects": "the vault thefts, the override code, the burner phone, and where Mira and the fifth case are",
            "concession": "that he is terrified and out of options, and that this was never about money",
            "opener": "You shouldn't be here. Not tonight, not now. Please - just go. I don't have anything to say to you.",
            "break": {
                "type": "threshold_any",
                "pool": ["vault-ledger", "gate-camera", "burner-phone", "proof-of-life-photo", "bricker-account"],
                "count": 2,
            },
        },
        {
            "id": "doss",
            "name": "Corporal Wyatt Doss",
            "sprite": "doss",
            "role": "Vault NCO, Fort Callow Special Weapons Depot",
            "personality": (
                "By-the-book to the point of anxiety, now visibly unraveling because the book "
                "let him down. Not devious - someone who trusted rank over instinct and is "
                "starting to understand the cost. Overexplains procedure when nervous, which is "
                "most of the time now. Clipped military phrasing, 'sir' and 'ma'am' on reflex."
            ),
            "publicAlibi": (
                "He was on duty exactly as logged, every night in question. He signed off same "
                "as always, following procedure to the letter - which, he keeps pointing out, is "
                "exactly the problem."
            ),
            "hiddenTruth": (
                "He countersigned all five checkouts now missing, every night Thorne told him it "
                "was 'already cleared with the Colonel' using her old override code. He didn't "
                "check. He's spent the morning quietly re-reading the log himself, terrified of "
                "what it means. He knows nothing about any blackmail or Mira - genuinely no idea "
                "why, only that his name is on all of it."
            ),
            "motive": "Fear of losing his rating and being blamed for a pattern he only now understands.",
            "protects": "very little - he wants someone to walk through the pattern with him and confirm what it means",
            "concession": "that he never once called to confirm the override, all five times",
            "opener": "You're here about the audit. I already gave my statement, but - go ahead, ask. I signed off. Same as always.",
            "break": {
                "type": "evidence_plus_question",
                "evidence": "vault-ledger",
                "angle": "asking him plainly, directly, what the ledger pattern actually means",
            },
        },
        {
            "id": "ashworth",
            "name": "Colonel Margaret Ashworth",
            "sprite": "ashworth",
            "role": "Battalion Commander, Fort Callow",
            "personality": (
                "Composed, precise, carries command like a second skin - and is using every bit "
                "of that composure right now to not fall apart. Fiercely protective of the "
                "people under her, which is exactly what's compromising her. Guilt-driven rather "
                "than self-interested. Formal, economical sentences; deflects with rank."
            ),
            "publicAlibi": (
                "She was off-base at a command dinner for most of the week in question - easily "
                "confirmed. Whatever the detective needs, she says, ask it once, and ask it like "
                "they intend to use the answer."
            ),
            "hiddenTruth": (
                "The override code on all five unauthorized checkouts is hers - issued to her "
                "years ago as a junior officer's adjutant, never formally retired. She had no "
                "idea it still worked until the audit. Separately, she has been sitting on an "
                "unfiled welfare-check flag for Thorne after his last deployment, delayed "
                "because she believed in him and didn't want one instinct to end his career."
            ),
            "motive": "Loyalty and guilt, not cover-up - but both facts together look exactly like she saw this coming.",
            "protects": "her record, and the fact that she sat on a concern about Thorne instead of filing it",
            "concession": "that she should have filed the flag months ago, and that not filing it may have cost time they didn't have",
            "opener": "I've already spoken to the Provost Marshal. Whatever you need from me, ask it once, and ask it like you intend to use the answer.",
            "break": {
                "type": "evidence_plus_question",
                "evidence": "vault-ledger",
                "angle": "showing her the log and asking specifically why she never filed the welfare-check flag on Thorne",
            },
        },
        {
            "id": "bricker",
            "name": "Lance Corporal Sam Bricker",
            "sprite": "bricker",
            "role": "Motor Pool Mechanic, Fort Callow - Thorne's oldest friend",
            "personality": (
                "Loyal to a fault, protective, running on two days of bad sleep. Defensive and a "
                "little combative at first - sees the detective as a threat to his friend, not "
                "help. Underneath it he's scared and ashamed he hasn't done more. Informal, "
                "quick to deflect with sarcasm or irritation."
            ),
            "publicAlibi": (
                "He hasn't seen Elias either, if this is about him. Something's off with him "
                "lately, sure, but that's not a crime. He has no vault access and was never on "
                "the checkout log."
            ),
            "hiddenTruth": (
                "Two nights ago Elias showed up wrecked and told him, in pieces, that 'they have "
                "her' and that he was 'almost done.' Bricker assumed something bad but "
                "survivable - debt, maybe worse - and has NO idea it involves stolen military "
                "ordnance or any terrorist group. He is lying purely to protect Elias from what "
                "he thinks is smaller, more ordinary trouble."
            ),
            "motive": "Protecting his best friend from what he wrongly assumes is a smaller kind of trouble.",
            "protects": "the visit two nights ago, the phrase 'they have her', Mira's absence, and the fishing cabin on Salt Row",
            "concession": "none, until he understands the real scale - pressure and evidence only make him dig in further",
            "opener": "Look, if this is about Elias, I haven't seen him either, alright? Something's off with him lately, sure. That's not a crime, last I checked.",
            "break": {
                "type": "conversational_trigger",
                "concepts": ["scale", "compact", "leverage"],
                "keyword_backstop": {
                    "scale": ["level a city block", "level several city block", "vsp-5", "vesper",
                              "demolition charge", "five case", "military ordnance", "weapons"],
                    "compact": ["cinder compact"],
                    "leverage": ["mira", "his wife", "her life", "hostage", "ransom"],
                },
            },
        },
    ],
    "evidence": [
        {
            "id": "vault-ledger",
            "name": "Vault Checkout Ledger",
            "summary": "Five checkouts, one dormant override code, all countersigned by Doss.",
            "detail": (
                "A terminal bolted to the vault's outer wall, logging every checkout by badge, "
                "time, and countersignature. Five entries over the last twelve nights stand out: "
                "the same override code on every one, issued to 'M. ASHWORTH, ADJT' years ago. "
                "Cpl. Doss countersigned all five."
            ),
            "contradicts": "The idea that nobody knew which code would still work, or who was on duty to sign off on it.",
            "pressure": 25,
            "found_text": (
                "A terminal bolted to the vault wall. Five checkouts over twelve nights, all on "
                "one long-dormant override code - issued to Colonel Ashworth years ago - and all "
                "countersigned by the same corporal."
            ),
        },
        {
            "id": "gate-camera",
            "name": "Motor Pool Gate Camera Footage",
            "summary": "Thorne's truck out after-hours all five nights; a masked handoff on the last.",
            "detail": (
                "A cracked monitor cycling through a week of grainy footage. On all five nights "
                "matching the ledger, one truck logs out after hours: registered to Staff "
                "Sergeant Elias Thorne. On the most recent night, it catches him stopped roadside "
                "half a mile out, meeting a masked figure who takes something from his truck bed."
            ),
            "contradicts": "His claim that he's been at the vault, on the road, or home - nothing else.",
            "pressure": 30,
            "requires": "vault-ledger",
            "locked_text": "Hours of grainy timestamped footage. Without knowing which five nights to look at, it's just traffic.",
            "found_text": (
                "The ledger's five nights, cross-checked against the gate log. Thorne's truck, out "
                "after hours, every time. The last clip: he meets a masked figure roadside, hands "
                "something over, and drives on - not toward home."
            ),
        },
        {
            "id": "matchbook",
            "name": "Cinder Compact Matchbook",
            "summary": "Dropped at the roadside meeting point. Half-legible note: Salt Row, Dock 4.",
            "detail": (
                "Plain black cover, no name, a single stamped mark near the corner - already "
                "linked to the Cinder Compact's last two jobs. Inside the flap, in ballpoint, "
                "half rubbed away by rain: 'SALT ROW - DOCK 4.'"
            ),
            "contradicts": "The idea that this theft has nothing to do with the Cinder Compact.",
            "pressure": 15,
            "found_text": (
                "A matchbook in the gravel where the gate camera caught the handoff. The mark "
                "matches the Cinder Compact's last two bombings. Inside the flap: 'SALT ROW - "
                "DOCK 4,' half washed out by rain."
            ),
        },
        {
            "id": "struggle-kitchen",
            "name": "Signs of a Struggle",
            "summary": "A shattered mug, a shoved-back chair, nothing packed. She didn't walk out.",
            "detail": (
                "Two mugs in the Thorne kitchen - one full and cold, one shattered on the floor "
                "and never swept up. A chair pushed back hard enough to scuff the tile. Nothing "
                "missing that a woman packing a bag would take - no coat, no keys, no shoes."
            ),
            "contradicts": "Any suggestion that Mira Thorne left on her own.",
            "pressure": 15,
            "found_text": (
                "The kitchen. A shattered mug never cleaned up, a chair shoved back hard, and "
                "nothing missing that anyone leaving willingly would have taken."
            ),
        },
        {
            "id": "burner-phone",
            "name": "The Burner Phone",
            "summary": "Hidden behind a garage shelf. One contact, a thread naming a countdown.",
            "detail": (
                "A prepaid phone tucked behind a paint shelf in the garage, screen cracked, one "
                "saved contact with no name. The thread underneath: a countdown, an address "
                "changed twice, and one line that doesn't need explaining."
            ),
            "contradicts": "Any claim that he isn't being pressured by anyone, or that he has something to sell rather than a debt to pay.",
            "pressure": 25,
            "found_text": (
                "Behind the paint shelf in the garage, a phone, screen cracked. One contact, no "
                "name. A thread of threats - a countdown, an address changed twice, and 'her for "
                "the last one, tonight, or you'll wish it was you.'"
            ),
        },
        {
            "id": "proof-of-life-photo",
            "name": "Proof-of-Life Photo",
            "summary": "Mira, holding a dated newspaper, four days ago.",
            "detail": (
                "Wedged in the same gap as the phone, face down. A woman on a folding chair "
                "against bare concrete, holding a folded newspaper. On the back, in pencil, a "
                "date - four days ago."
            ),
            "contradicts": "Any doubt that this is real, current, and ongoing.",
            "pressure": 20,
            "requires": "burner-phone",
            "locked_text": "There's a gap behind this shelf, but nothing to see until you know to look for it.",
            "found_text": (
                "A photo, face down behind the shelf. Mira Thorne, on a folding chair against bare "
                "concrete, holding up a dated newspaper. Proof she was alive four days ago - and "
                "proof someone wanted that fact kept close at hand."
            ),
        },
        {
            "id": "bricker-account",
            "name": "Bricker's Account",
            "summary": "What Elias told him, two nights ago, once he finally says it.",
            "detail": (
                "Sam Bricker's account, once he understood what he was actually protecting: that "
                "Elias came to him wrecked, said 'they have her,' and that it would 'be over "
                "soon' - and that the two of them know a fishing cabin on Salt Row nobody else "
                "would think to check."
            ),
            "contradicts": "Every version of events where Thorne is acting alone, for money, or by choice.",
            "pressure": 25,
            "sourced": "dialogue",
        },
    ],
    "conviction": {
        "culprit": "thorne",
        "strong": {
            "pool": ["vault-ledger", "gate-camera", "burner-phone", "proof-of-life-photo", "bricker-account"],
            "requires_count": 2,
            "minPressure": 55,
        },
    },
    "endings": {
        "correct_strong": {
            "caption": "COERCED, NOT SOLD",
            "prose": (
                "Grim relief, not triumph. Confronted with the evidence, Thorne gives up the "
                "cabin and the midnight handoff before you have to ask twice. Officers move on "
                "Salt Row in time; the fifth case is recovered, and - just barely - so is Mira, "
                "traced through the courier caught at the drop. Thorne is arrested, but the "
                "report on his desk starts with 'coerced' instead of 'sold,' and Ashworth is "
                "already fighting to keep it that way."
            ),
        },
        "wrong_suspect": {
            "caption": "THE WRONG NAME",
            "prose": (
                "Not a game over, but a costly one. Whoever you named is cleared within hours, "
                "and every one of those hours mattered. Midnight comes and goes with no one "
                "moving on Salt Row. The fifth case changes hands on schedule. Thorne is picked "
                "up two days later, ruined and alone - Mira is never found in time, and he stops "
                "talking about her entirely."
            ),
        },
        "correct_thin": {
            "caption": "RIGHT NAME, THIN CASE",
            "prose": (
                "Right name, thin case. You name Thorne but can't back it with much, and the "
                "confrontation goes differently - he shuts down instead of breaking, gives up the "
                "case but not the cabin, not the deadline, not Mira. The fifth charge turns up "
                "days later in a raid, empty-handed on everything else. It's filed as a "
                "straightforward theft. Nobody finds out why, and nobody goes looking for her."
            ),
        },
    },
    "solution": (
        "Staff Sergeant Elias Thorne stole all five VSP-5 cases from Fort Callow's vault over "
        "twelve nights, using Colonel Ashworth's long-dormant override code to satisfy the "
        "two-signature rule without her knowledge - Cpl. Doss, trusting him, countersigned every "
        "one. He was paying a ransom in stolen ordnance: the Cinder Compact took his wife Mira "
        "four days before the first theft and has been trading her life for one case at a time "
        "ever since. The fifth case, and the final handoff for Mira, waited at the family's "
        "fishing cabin on Salt Row, due at midnight."
    ),
}

SUSPECTS_BY_ID = {s["id"]: s for s in CASE["suspects"]}
EVIDENCE_BY_ID = {e["id"]: e for e in CASE["evidence"]}
