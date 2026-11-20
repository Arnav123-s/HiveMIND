"""Fit two small regularized linear classifiers on English work orders."""
from collections import Counter
from functools import lru_cache
import math
import re

# Source skills contain no filtered grouped tasks and no smallest-group numeric sums.
EXAMPLES = {
    "CP": [
        "Count all records.", "How many entries are in the table?", "Give me the number of rows.",
        "What is the tally of visits?", "How many records come from shop Oak?",
        "Count the deliveries to Lake.", "Report the number of calls logged by Red.",
        "Count each matching order only once.", "How many observations did we record?",
    ],
    "SP": [
        "Add the weights.", "What is the sum of all quantities?", "Report the total number of units.",
        "How many items were shipped altogether?", "Give the combined amount in dollars.",
        "How much weight did we handle overall?", "Total the costs.", "What is total revenue for Oak?",
        "Add up the quantities recorded at East.", "How many minutes were used in total?",
    ],
    "CG": [
        "Count records by shop.", "How many records are there for each owner?",
        "Give the number of observations per class.", "Tabulate the number of orders by route.",
        "A breakdown of visits for each store is needed.", "For every group show its row count.",
        "Give me counts by supplier.", "Tally the entries separately for each district.",
    ],
    "SG": [
        "Sum quantity by shop.", "Show the total weight for each owner.",
        "For every group return the combined quantity.", "Break down units by category.",
        "Add up the amounts separately per route.", "Give a mapping of district to total revenue.",
        "Group the rows by project and sum their hours.", "What are the totals per team?",
    ],
    "CH": [
        "Which group has the most records?", "Name the owner with the largest number of calls.",
        "Find the shop that occurs most often.", "Return the category with the highest count.",
        "Which team has the most entries?", "Give the name of the busiest site by number of visits.",
    ],
    "CL": [
        "Which district has the fewest records?", "What category occurs least often?",
        "Return the owner with the smallest number of entries.", "Find the group with the lowest count.",
        "Which label has the minimum tally?", "Which kind occurs the fewest times?",
    ],
    "SH": [
        "Which supplier has the largest total weight?", "Name the shop with the highest sum of units.",
        "Which category accounts for the most revenue?", "Give the group with the greatest total quantity.",
        "Return the owner with the maximum combined hours.", "Who contributed the highest amount overall?",
    ],
}


def features(text):
    words = re.findall(r"[a-z]+", text.casefold())
    words = [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]
    return set(words) | {a + "_" + b for a, b in zip(words, words[1:])}


class Classifier:
    def __init__(self, items):
        self.labels = sorted({label for _, label in items})
        self.weights = {label: Counter() for label in self.labels}
        vectors = [(sorted(features(text)), label) for text, label in items]
        # Class-balanced deterministic online multinomial logistic regression.
        frequency = Counter(y for _, y in items)
        for epoch in range(55):
            for x, truth in vectors:
                prob = self.probabilities(x)
                step = .32 / math.sqrt(1 + epoch / 8) * len(items) / (len(frequency) * frequency[truth])
                for label in self.labels:
                    delta = step * ((label == truth) - prob[label])
                    for term in x:
                        self.weights[label][term] += delta / math.sqrt(len(x))

    def probabilities(self, x):
        raw = {label: sum(self.weights[label][w] for w in x) / math.sqrt(max(len(x), 1))
               for label in self.labels}
        largest = max(raw.values())
        unnorm = {label: math.exp(v - largest) for label, v in raw.items()}
        total = sum(unnorm.values())
        return {label: v / total for label, v in unnorm.items()}

    def predict(self, text):
        probs = self.probabilities(sorted(features(text)))
        return max(probs, key=probs.get)


@lru_cache(maxsize=1)
def models():
    data = [(text, code) for code, texts in EXAMPLES.items() for text in texts]
    return (Classifier([(s, c[0]) for s, c in data]), Classifier([(s, c[1]) for s, c in data]),
            Classifier(data))
