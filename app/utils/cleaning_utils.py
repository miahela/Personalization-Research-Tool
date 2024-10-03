import re
from typing import Dict

from nameparser import HumanName


def clean_name(full_string) -> Dict[str, str]:
    # Split the string into name and qualifications
    parts = re.split(r',\s*(?=[A-Z]{2,})', full_string, 1)
    name_part = parts[0]
    qualifications = parts[1] if len(parts) > 1 else ''

    # Parse the name
    name = HumanName(name_part)

    # If the parsed name looks incorrect, try alternative parsing
    if not name.first or not name.last:
        words = name_part.split()
        if len(words) >= 2:
            name.first = words[0]
            name.last = words[-1]
            name.middle = ' '.join(words[1:-1]) if len(words) > 2 else ''

    return {
        'first_name': name.first,
        'middle_name': name.middle,
        'last_name': name.last,
        'qualifications': qualifications.strip()
    }
