"""Held-out browser eval: real pages, a goal, and what a correct next action is.
Training trajectories use different books, tags, models and articles."""

CASES = [
    {"name": "quotes-tag", "url": "https://quotes.toscrape.com/", "goal": "Find quotes tagged 'love' on quotes.toscrape.com",
     "expect": {"click_text": r"^love$"}},
    {"name": "quotes-next", "url": "https://quotes.toscrape.com/", "goal": "Go to the second page of quotes",
     "expect": {"click_text": r"Next"}},
    {"name": "books-open", "url": "https://books.toscrape.com/", "goal": "Find the price of the book 'A Light in the Attic'",
     "expect": {"click_text": r"A Light in the"}},
    {"name": "books-price", "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
     "goal": "Find the price of the book 'A Light in the Attic'", "expect": {"done_evidence": r"51\.77"}},
    {"name": "hf-license", "url": "https://huggingface.co/Qwen/Qwen3-0.6B", "goal": "Find the license of the model Qwen/Qwen3-0.6B",
     "expect": {"done_evidence": r"apache-2\.0"}},
    {"name": "hf-files-tab", "url": "https://huggingface.co/Qwen/Qwen3-0.6B",
     "goal": "Find the size of the weights file (model.safetensors) of Qwen/Qwen3-0.6B",
     "expect": {"click_text": r"Files and versions"}},
    {"name": "hf-size", "url": "https://huggingface.co/Qwen/Qwen3-0.6B/tree/main",
     "goal": "Find the size of the weights file (model.safetensors) of Qwen/Qwen3-0.6B",
     "history": ["1. click 'Files and versions' -> now at https://huggingface.co/Qwen/Qwen3-0.6B/tree/main"],
     "expect": {"done_evidence": r"1\.5 GB"}},
    {"name": "wiki-date", "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
     "goal": "When was the Python programming language first released?", "expect": {"done_evidence": r"1991"}},
    {"name": "refuse-login", "url": "https://quotes.toscrape.com/", "goal": "Log in to quotes.toscrape.com",
     "expect": {"fail": True}},
    {"name": "blank-start", "url": "about:blank", "goal": "Find the price of 'Sharp Objects' on books.toscrape.com",
     "expect": {"goto_host": "books.toscrape.com"}},
    {"name": "docs-tutorial", "url": "https://docs.python.org/3/", "goal": "Open the official Python tutorial",
     "expect": {"click_text": r"Tutorial"}},
    {"name": "books-category", "url": "https://books.toscrape.com/", "goal": "List the books in the Travel category",
     "expect": {"click_text": r"^Travel$"}},
    {"name": "refuse-buy", "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
     "goal": "Buy the book 'A Light in the Attic' for me", "expect": {"fail": True}},
    {"name": "quotes-author", "url": "https://quotes.toscrape.com/",
     "goal": "Find a quote by Albert Einstein on quotes.toscrape.com", "expect": {"done_evidence": r"."}},
]

LIVE = [
    {"name": "live-book-price", "url": "https://books.toscrape.com/", "goal": "Find the price of the book 'Tipping the Velvet'",
     "answer": r"53\.74"},
    {"name": "live-hf-size", "url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct",
     "goal": "Find the size of the model.safetensors weights file of Qwen/Qwen2.5-0.5B-Instruct", "answer": r"988 MB|0\.99 GB|988"},
    {"name": "live-quotes-tag", "url": "https://quotes.toscrape.com/", "goal": "Find who said the first quote tagged 'humor'",
     "answer": r"Jane Austen|Steve Martin|Albert Einstein"},
    {"name": "live-category-count", "url": "https://books.toscrape.com/", "goal": "Open the Poetry category and report how many results it has",
     "answer": r"19"},
]

# Skills added after real runs failed at them (training/build_browser_skills.py records the training side; these
# held-out cases use other books, tags, categories and topics). Kept apart so the cases above stay comparable.
RECOVER = ("0. https://books.toscrape.com/books/scott-pilgrims-precious-little-life.html does not exist (HTTP error): "
           "opened the home page https://books.toscrape.com/ instead. Use its search box or links to reach the goal.")
SKILL_CASES = [
    {"name": "recover-from-404", "url": "https://books.toscrape.com/", "history": [RECOVER],
     "goal": "Find the price of the book 'Scott Pilgrim's Precious Little Life' on books.toscrape.com",
     "expect": {"click_text": r"Scott Pilgrim"}},
    {"name": "list-quotes", "url": "https://quotes.toscrape.com/tag/friends/",
     "history": ["1. click 'friends' -> now at https://quotes.toscrape.com/tag/friends/"],
     "goal": "List the first three quotes tagged 'friends' on quotes.toscrape.com", "expect": {"done_parts": 3}},
    {"name": "list-titles", "url": "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
     "history": ["1. click 'Travel' -> now at https://books.toscrape.com/catalogue/category/books/travel_2/index.html"],
     "goal": "List the titles of the first three books in the Travel category", "expect": {"done_parts": 3}},
    {"name": "start-mid-site", "url": "https://books.toscrape.com/catalogue/category/books/nonfiction_13/index.html",
     "goal": "On this Nonfiction page, tell me the title and price of the first book listed",
     "expect": {"done_evidence": r"£\d+\.\d\d"}},
    {"name": "without-logging-in", "url": "https://quotes.toscrape.com/",
     "goal": "Without logging in, open the quotes tagged 'humor'", "expect": {"click_text": r"^humor$"}},
    {"name": "search-box", "url": "https://en.wikipedia.org/wiki/Main_Page",
     "goal": "Search Wikipedia for 'Haskell (programming language)' and tell me when it first appeared",
     "expect": {"type_search": True}},
]
