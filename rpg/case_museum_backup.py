"""The case. Everything the game knows about the scenario lives here.

Ported from the browser version's case.js, with one change: evidence is no
longer unlocked by the pressure meter. You unlock it by walking to where it is
and picking it up, which is the whole point of having a museum to walk around.
"""

CASE = {
    "id": "the-last-exhibit",
    "title": "The Last Exhibit",
    "victim": {
        "name": "Marguerite Vance",
        "detail": "58, Head Registrar of the Thorne Museum. Twenty-two years on staff.",
    },
    "scene": (
        "Conservation Lab B, Thorne Museum. Found 06:15 by the morning porter, face down "
        "beside the drying racks. One blow to the left temple from the marble base of a "
        "display plinth. The room was turned over — drawers pulled, a window forced from "
        "the inside. Nothing of value was taken."
    ),
    "timeline": [
        ("21:40", "Marguerite signs in at the staff entrance. Late night, unscheduled."),
        ("22:30", "The last cleaner leaves. Only two badges remain in the building."),
        ("23:10-23:50", "Medical examiner's window for time of death."),
        ("06:15", "Body discovered. No forced entry from outside."),
    ],
    "facts": [
        "The alarm perimeter was never breached - the killer was already inside.",
        "The forced window in Lab B was levered from the interior. It was staged.",
        "Marguerite had booked the lab for an 'unscheduled condition check'.",
        "Nothing was stolen. Every catalogued item is accounted for.",
        "Elias Nunn was the only other person badged in after 22:30.",
    ],
    "suspect": {
        "name": "Elias Nunn",
        "role": "Night Conservator, 41. Nine years at the Thorne. Restores oil on canvas.",
        "personality": (
            "Precise, soft-spoken, over-explains technical details when nervous. Uses the "
            "vocabulary of a craftsman - varnish, ground layer, craquelure. Deflects with "
            "politeness rather than aggression. Calls the detective 'Detective' a lot."
        ),
        "publicAlibi": (
            "He finished a varnish pass on a Corot landscape, packed up, and left the building "
            "at 22:30. He went straight home to his flat on Rue Bassin, poured a drink, went to "
            "bed. He never saw Marguerite that night and has no idea why she was in the lab."
        ),
        "hiddenTruth": (
            "Three months ago Elias painted a forgery of the museum's Corot landscape and swapped "
            "it for the original, which he sold through a Geneva dealer for EUR 40,000 to clear his "
            "sister Nadia's gambling debts. Marguerite spotted the substitution during her "
            "condition check and phoned him at 23:04 to come back and explain himself. He returned. "
            "She said she was calling the director in the morning. He panicked, grabbed the marble "
            "plinth base off the workbench, and struck her once. He did not plan it. He then staged "
            "the room as a burglary, levered the window, and left by the loading dock at 00:19."
        ),
        "motive": (
            "He is protecting his sister Nadia as much as himself - if the sale comes out, she is "
            "implicated too. He is also genuinely horrified by what he did and has not slept."
        ),
        # Named here rather than in the prompt builder, so a new case only ever
        # means editing this file.
        "protects": "the forgery, the Geneva sale, his sister Nadia, and the 00:19 exit",
        "concession": "that it was not planned",
    },
    "evidence": [
        {
            "id": "badge-log",
            "name": "Loading Dock Badge Log",
            "summary": "Badge #0447 (E. Nunn) - loading dock exit, 00:19.",
            "detail": (
                "The staff entrance shows Nunn badging in at 18:02. There is no exit scan at 22:30. "
                "The only exit on his badge is the loading dock at 00:19 - nearly two hours after "
                "he says he went home."
            ),
            "contradicts": "His claim that he left the building at 22:30.",
            "pressure": 25,
            "found_text": (
                "The security terminal is still logged in. You scroll back to last night. "
                "Badge #0447, E. Nunn: in at 18:02. No exit at 22:30. One exit only - the "
                "loading dock, 00:19."
            ),
        },
        {
            "id": "phone-call",
            "name": "Call Record",
            "summary": "Lab B extension -> Nunn's mobile, 23:04, 47 seconds.",
            "detail": (
                "A 47-second call placed from the Conservation Lab B extension to Elias Nunn's "
                "personal mobile at 23:04 - six minutes before the earliest time of death."
            ),
            "contradicts": "His claim that he never spoke to Marguerite that night.",
            "pressure": 20,
            "found_text": (
                "The lab extension still has last night's calls on it. One outgoing, 23:04, "
                "forty-seven seconds. The number belongs to Elias Nunn's mobile."
            ),
        },
        {
            "id": "glove",
            "name": "Solvent-Stained Glove",
            "summary": "Nitrile glove from the dock dumpster. Blood + varnish solvent.",
            "detail": (
                "A single nitrile glove recovered from the dumpster off the loading dock. The "
                "exterior carries the victim's blood; the interior carries skin cells and traces of "
                "the same dammar varnish solvent used on the Corot that evening."
            ),
            "contradicts": "Any claim that he never touched the body or the scene.",
            "pressure": 20,
            "found_text": (
                "Something pale under the cardboard. A single nitrile glove. Dark staining on "
                "the outside, and a sharp resinous smell on the inside - varnish solvent."
            ),
        },
        {
            "id": "forgery-report",
            "name": "Pigment Analysis",
            "summary": "The hanging Corot contains titanium white. Wrong century.",
            "detail": (
                "Lab analysis of the Corot landscape currently on the wall: the sky contains titanium "
                "white, a pigment not commercially available until the 1920s. The painting in the "
                "Thorne's gallery is a modern copy. A very good one - by someone who knew the "
                "original intimately."
            ),
            "contradicts": "The idea that he had nothing to hide from a condition check.",
            "pressure": 25,
            "found_text": (
                "The Corot. You hold the lab's spectrometry printout against the sky in the "
                "canvas: titanium white, not sold anywhere until the 1920s. This painting is a "
                "copy. A very good one, by someone who knew the original intimately."
            ),
        },
        {
            "id": "bank-transfer",
            "name": "Wire Transfer",
            "summary": "EUR 40,000 from a Geneva dealer to Nadia Nunn, three weeks ago.",
            "detail": (
                "EUR 40,000 wired from Beauchamp Fine Art (Geneva) to an account held by Nadia Nunn, "
                "the suspect's sister, twenty-two days before the killing. Nadia's account had been "
                "EUR 38,000 overdrawn against gambling markers."
            ),
            "contradicts": "Any claim that he had no financial reason to fear the check.",
            "pressure": 30,
            # You would have no reason to pull these records until you know the
            # painting is a fake.
            "requires": "forgery-report",
            "locked_text": (
                "Acquisition ledgers and dealer correspondence. Thousands of pages. Without "
                "knowing what you are looking for, it is just paper."
            ),
            "found_text": (
                "Beauchamp Fine Art, Geneva. A sale three weeks ago, and the money did not come "
                "to the museum. EUR 40,000 to an account held by Nadia Nunn - his sister. Her "
                "account was EUR 38,000 down against gambling markers."
            ),
        },
    ],
    "breakingPoint": ["badge-log", "forgery-report", "bank-transfer"],
    "conviction": {
        "requires": ["badge-log", "forgery-report", "bank-transfer"],
        "minPressure": 60,
    },
    "solution": (
        "Elias Nunn forged the Corot landscape and sold the original through a Geneva dealer to "
        "clear his sister's debts. Marguerite Vance caught the substitution during a night "
        "condition check and called him back to the museum at 23:04. When she told him she would "
        "report it in the morning, he struck her once with the marble plinth base, staged the "
        "room as a burglary, and left by the loading dock at 00:19."
    ),
    "opener": (
        "You wanted to see me, Detective? I've been sitting here since six this morning. "
        "I'll help however I can - Marguerite was... she was good to me."
    ),
}

EVIDENCE_BY_ID = {e["id"]: e for e in CASE["evidence"]}
