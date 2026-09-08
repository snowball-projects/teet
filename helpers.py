

CLASSES = [
    'Champion', 'Avenger', 'White Wizard', 'Arch Sage', 'Sniper', 'Monster Hunter', 'Phantom Assassin',
    'Master Stalker', 'Grand Templar', 'Dark ArchTemplar', 'Hierophant', 'Prophetess', 'Professional Witcher',
    'Grand Inquisitor', 'Summoner', 'Rune Master (Bear)', 'Rune Master (Wolf)', 'Jounin', 'Annihilator', 'Sky Sorceress',
    'Lightbinder', 'Mystic', 'Stargazer', 'Valkryie', 'Paladin', 'Rhapsody', 'Mythsong', 'Demon Incarnate'
]

ITEM_CLASS_MAP = {
    'All': CLASSES,
    'Melee': [
        'Champion', 'Avenger', 'Phantom Assassin', 'Master Stalker', 'Dark ArchTemplar', 'Professional Witcher', 'Grand Inquisitor', 
        'Rune Master (Bear)', 'Rune Master (Wolf)', 'Jounin', 'Annihilator', 'Valkryie', 'Paladin', 'Demon Incarnate'
    ],
    'Intelligence': [
        'White Wizard', 'Arch Sage', 'Grand Templar', 'Hierophant', 'Prophetess', 'Summoner', 'Rune Master (Bear)',
        'Rune Master (Wolf)', 'Sky Sorceress', 'Lightbinder', 'Mystic', 'Stargazer', 'Rhapsody', 'Mythsong', 'Demon Incarnate'
    ],
    'Archer': ['Sniper', 'Monster Hunter', 'Demon Incarnate'],
    'Melee Agility': ['Phantom Assassin', 'Master Stalker', 'Dark ArchTemplar', 'Professional Witcher', 'Jounin', 'Annihilator', 'Demon Incarnate'],
    'Tank': ['Champion', 'Avenger', 'Rune Master (Bear)', 'Valkryie', 'Demon Incarnate'],
    'Chunin': ['Jounin', 'Demon Incarnate'],
    'Inquisitor': ['Grand Inquisitor', 'Demon Incarnate'],
    'Shapeshifter': ['Rune Master (Bear)', 'Rune Master (Wolf)', 'Demon Incarnate'],
    'Druid': ['Summoner', 'Rune Master (Bear)', 'Rune Master (Wolf)', 'Demon Incarnate']
}

CLASS_PRIMARY_ATTR = {
    "Str": [
        "Champion", "Avenger", "Grand Inquisitor", "Annihilator", "Valkryie", "Paladin", "Demon Incarnate"
    ],
    "Agi": [
        "Sniper", "Monster Hunter", "Phantom Assassin", "Master Stalker", "Dark ArchTemplar", "Professional Witcher", "Jounin"
    ],
    "Int": [
        "White Wizard", "Arch Sage", "Grand Templar", "Hierophant", "Prophetess", "Summoner", "Rune Master (Bear)", "Rune Master (Wolf)", 
        "Sky Sorceress", "Lightbinder", "Mystic", "Stargazer", "Rhapsody", "Mythsong"
    ]
}

for key in ITEM_CLASS_MAP:
    if "Demon Incarnate" not in ITEM_CLASS_MAP[key]:
        ITEM_CLASS_MAP[key].append("Demon Incarnate")