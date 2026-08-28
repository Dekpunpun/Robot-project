/* ---------------------------------------------------------------------------
 * CASE DEFINITION
 *
 * Everything the game knows about a scenario lives in this one object. To ship
 * a new case, copy this file, rewrite the values, and point index.html at it.
 * No other file needs to change.
 * ------------------------------------------------------------------------- */

const CASE = {
  id: "the-last-exhibit",
  title: "The Last Exhibit",

  victim: {
    name: "Marguerite Vance",
    detail: "58, Head Registrar of the Thorne Museum. Twenty-two years on staff.",
  },

  scene:
    "Conservation Lab B, Thorne Museum. Found 06:15 by the morning porter, face down " +
    "beside the drying racks. One blow to the left temple from the marble base of a " +
    "display plinth. The room was turned over — drawers pulled, a window forced from " +
    "the inside. Nothing of value was taken.",

  timeline: [
    { time: "21:40", text: "Marguerite signs in at the staff entrance. Late night, unscheduled." },
    { time: "22:30", text: "The last cleaner leaves. Only two badges remain in the building." },
    { time: "23:10–23:50", text: "Medical examiner's window for time of death." },
    { time: "06:15", text: "Body discovered. Alarm system shows no forced entry from outside." },
  ],

  facts: [
    "The museum's alarm perimeter was never breached — the killer was already inside.",
    "The forced window in Lab B was levered from the interior. It was staged.",
    "Marguerite had booked the conservation lab for an 'unscheduled condition check'.",
    "Nothing was stolen. Every catalogued item is accounted for.",
    "Elias Nunn was the only other person badged into the building after 22:30.",
  ],

  suspect: {
    name: "Elias Nunn",
    pronouns: "he/him",
    role: "Night Conservator, 41. Nine years at the Thorne. Restores oil on canvas.",
    portraitInitials: "EN",

    personality:
      "Precise, soft-spoken, over-explains technical details when nervous. Uses the " +
      "vocabulary of a craftsman — varnish, ground layer, craquelure. Deflects with " +
      "politeness rather than aggression. Calls the detective 'Detective' a lot.",

    publicAlibi:
      "He finished a varnish pass on a Corot landscape, packed up, and left the building " +
      "at 22:30. He went straight home to his flat on Rue Bassin, poured a drink, went to " +
      "bed. He never saw Marguerite that night and has no idea why she was in the lab.",

    hiddenTruth:
      "Three months ago Elias painted a forgery of the museum's Corot landscape and swapped " +
      "it for the original, which he sold through a Geneva dealer for €40,000 to clear his " +
      "sister Nadia's gambling debts. Marguerite spotted the substitution during her " +
      "condition check and phoned him at 23:04 to come back and explain himself. He returned. " +
      "She said she was calling the director in the morning. He panicked, grabbed the marble " +
      "plinth base off the workbench, and struck her once. He did not plan it. He then staged " +
      "the room as a burglary, levered the window, and left by the loading dock at 00:19.",

    motive:
      "He is protecting his sister Nadia as much as himself — if the sale comes out, she is " +
      "implicated too. He is also genuinely horrified by what he did and has not slept.",
  },

  /* ---- EVIDENCE -----------------------------------------------------------
   * available : on the board from the start
   * unlock    : { pressure: N } or { afterPresenting: "<evidence id>" }
   * pressure  : how much the meter moves if this lands a real contradiction
   * contradicts: shown to the model so it knows what this evidence breaks
   * ---------------------------------------------------------------------- */
  evidence: [
    {
      id: "badge-log",
      name: "Loading Dock Badge Log",
      icon: "🪪",
      summary: "Badge #0447 (E. Nunn) — loading dock exit, 00:19.",
      detail:
        "The staff entrance shows Nunn badging in at 18:02. There is no exit scan at 22:30. " +
        "The only exit on his badge is the loading dock at 00:19 — nearly two hours after " +
        "he says he went home.",
      contradicts: "His claim that he left the building at 22:30.",
      pressure: 25,
      available: true,
    },
    {
      id: "phone-call",
      name: "Call Record",
      icon: "📞",
      summary: "Lab B extension → Nunn's mobile, 23:04, 47 seconds.",
      detail:
        "A 47-second call placed from the Conservation Lab B extension to Elias Nunn's " +
        "personal mobile at 23:04 — six minutes before the earliest time of death.",
      contradicts: "His claim that he never spoke to Marguerite that night.",
      pressure: 20,
      available: true,
    },
    {
      id: "glove",
      name: "Solvent-Stained Glove",
      icon: "🧤",
      summary: "Nitrile glove, dumpster behind the loading dock. Blood + varnish solvent.",
      detail:
        "A single nitrile glove recovered from the dumpster off the loading dock. The " +
        "exterior carries the victim's blood; the interior carries skin cells and traces of " +
        "the same dammar varnish solvent used on the Corot that evening.",
      contradicts: "Any claim that he never touched the body or the scene.",
      pressure: 20,
      available: true,
    },
    {
      id: "forgery-report",
      name: "Pigment Analysis",
      icon: "🔬",
      summary: "The hanging Corot contains titanium white. Wrong century.",
      detail:
        "Lab analysis of the Corot landscape currently on the wall: the sky contains titanium " +
        "white, a pigment not commercially available until the 1920s. The painting in the " +
        "Thorne's gallery is a modern copy. A very good one — by someone who knew the " +
        "original intimately.",
      contradicts: "The idea that he had nothing to hide from a condition check.",
      pressure: 25,
      unlock: { pressure: 30 },
    },
    {
      id: "bank-transfer",
      name: "Wire Transfer",
      icon: "💶",
      summary: "€40,000 from a Geneva dealer to Nadia Nunn, three weeks ago.",
      detail:
        "€40,000 wired from Beauchamp Fine Art (Geneva) to an account held by Nadia Nunn, " +
        "the suspect's sister, twenty-two days before the killing. Nadia's account had been " +
        "€38,000 overdrawn against gambling markers.",
      contradicts: "Any claim that he had no financial reason to fear the condition check.",
      pressure: 30,
      unlock: { afterPresenting: "forgery-report" },
    },
  ],

  /* Present all of these and the suspect has nowhere left to stand. */
  breakingPoint: ["badge-log", "forgery-report", "bank-transfer"],

  /* What a conviction actually requires: placing him at the scene, and motive. */
  conviction: {
    verdict: "guilty",
    requires: ["badge-log", "forgery-report", "bank-transfer"],
    minPressure: 60,
  },

  solution:
    "Elias Nunn forged the Corot landscape and sold the original through a Geneva dealer to " +
    "clear his sister's debts. Marguerite Vance caught the substitution during a night " +
    "condition check and called him back to the museum at 23:04. When she told him she would " +
    "report it in the morning, he struck her once with the marble plinth base, staged the " +
    "room as a burglary, and left by the loading dock at 00:19.",

  opener:
    "You wanted to see me, Detective? I've been sitting out there since six this morning. " +
    "I'll help however I can — Marguerite was… she was good to me.",
};
