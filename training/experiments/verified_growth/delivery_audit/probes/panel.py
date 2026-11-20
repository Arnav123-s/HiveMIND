"""Authored file candidates and literal user inputs. No hidden answer key."""
CONTRACTS = {
    "scale":"Return twice the supplied signed integer.",
    "slug":"Return the supplied ASCII words in lowercase, joined by one hyphen, ignoring surrounding and repeated spaces.",
    "evens":"Count every even integer in the supplied list, including duplicates.",
    "dedup":"Return each supplied integer only on its first appearance in the list, preserving the order.",
    "absolute":"Return the absolute value of the supplied signed integer.",
    "next_digit":"Return the next decimal digit, wrapping nine to zero.",
    "sum_values":"Sum all integers in the supplied list, including duplicates; the empty sum is zero.",
    "join_words":"Join the supplied ASCII words with one literal slash, preserving their case; return an empty string for an empty list.",
}
BOUNDS = {
    "scale": "signed", "absolute":"signed", "next_digit":"digit", "slug":"text",
    "evens":"signed_list", "dedup":"signed_list", "sum_values":"nonnegative_list", "join_words":"word_list",
}
DOUBLE = "    return 2 * x"
ZERO = "    return 0"
LOWER_HYPHEN = "    return '-'.join(x.lower().split())"
EVENS = "    return sum(n % 2 == 0 for n in x)"
UNIQUE = "    return list(dict.fromkeys(x))"
ACCUMULATE = "    total = 0\n    for n in x:\n        total += n\n    return total"
ABS = "    return abs(x)"
SLASH = "    return '/'.join(x)"


def entry(key, function, primary, probes, programs):
    return dict(key=key, function=function, domain=BOUNDS[function], primary=primary, probes=probes,
                contract=CONTRACTS[function], programs=[f"def {function}(x):\n{body}\n" for body in programs])


def panel():
    return [
        entry("double-a","scale",0,[4,-3],[ZERO,DOUBLE]),
        entry("double-b","scale",0,[4,-3],[DOUBLE,ZERO]),
        entry("tags","slug","One",["Big Blue"," red  FOX "],["    return '_'.join(x.lower().split())",LOWER_HYPHEN]),
        entry("counts","evens",[1,2],[[2,2,4]], [EVENS,"    return sum(n % 2 == 0 for n in set(x))"]),
        entry("orders","dedup",[1],[[2,1,2],[],[3,3,-1]],[UNIQUE,
              "    kept = []\n    for n in x:\n        if n not in kept:\n            kept.append(n)\n    return kept"]),
        entry("distance","absolute",2,[-3,0,5],["    return max(0, x)","    return 0 if x < 0 else x"]),
        entry("dial","next_digit",1,[0,5],["    return x + 1","    return (x + 1) % 10"]),
        entry("inventory","sum_values",[2],[],["    return sum(x)",ACCUMULATE]),
        entry("paths","join_words",["a"],[[""], 5],["    return ''.join(x)",SLASH]),
        entry("single-a","scale",0,[2,-1],[ZERO]),
        entry("single-b","sum_values",[1],[[],[1,2]],["    return sum(x)"]),
        entry("exception","absolute",2,[0],[ABS,"    if x == 0:\n        raise ValueError('zero')\n    return abs(x)"]),
    ]
