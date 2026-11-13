# Muse's work — Muse's side

# Corpus v3 — sources and licenses

Built 2026-11-13 (UTC) by `make_corpus_v3.py` for Muse's side's BitNet lab.
Corpus v3 contains **only** openly-licensed / public-domain English text, from two
sources. Raw downloads live in `corpus-v3/raw/`; the builder's cleaning/tokenization
discipline is v2's (see `make_corpus_v3.py` header). Total raw text acquired:
**617,199,932 bytes (~617 MB)**.

## 1. Project Gutenberg — public domain

- **License status:** the underlying works are **public domain in the United States**
  (all published before 1930). Files were fetched from Project Gutenberg's official
  site, plain-text UTF-8 editions (`https://www.gutenberg.org/files/{id}/{id}-0.txt`),
  one request at a time with pacing. During the build, each book's Project Gutenberg
  header/footer (the license wrapper) is stripped — text is taken only between the
  `*** START OF THE PROJECT GUTENBERG EBOOK ***` and `*** END … ***` markers — so the
  corpus contains the public-domain works themselves, not Gutenberg's license text.
- **Acquired:** 67 books, 73,663,011 bytes, in `raw/gutenberg/pg{id}.txt`
  (fetch log: `raw/gutenberg/dl.log`).

| ID | Work | Bytes |
|---|---|---|
| 2600 | War and Peace — Leo Tolstoy | 3,359,405 |
| 1399 | Anna Karenina — Leo Tolstoy | 2,048,246 |
| 2701 | Moby Dick — Herman Melville | 1,234,646 |
| 135 | Les Misérables — Victor Hugo | 3,349,503 |
| 1184 | The Count of Monte Cristo — Alexandre Dumas | 2,704,417 |
| 996 | Don Quixote — Miguel de Cervantes | 2,391,549 |
| 145 | Middlemarch — George Eliot | 1,812,793 |
| 1023 | Bleak House — Charles Dickens | 2,025,044 |
| 766 | David Copperfield — Charles Dickens | 2,013,603 |
| 1400 | Great Expectations — Charles Dickens | 1,038,512 |
| 1260 | Jane Eyre — Charlotte Brontë | 1,044,063 |
| 768 | Wuthering Heights — Emily Brontë | 661,813 |
| 1342 | Pride and Prejudice — Jane Austen | 738,046 |
| 158 | Emma — Jane Austen | 897,582 |
| 6130 | The Iliad — Homer, tr. Samuel Butler | 1,115,936 |
| 1727 | The Odyssey — Homer, tr. Samuel Butler | 686,287 |
| 98 | A Tale of Two Cities — Charles Dickens | 771,600 |
| 2554 | Crime and Punishment — Fyodor Dostoevsky | 1,160,669 |
| 28054 | The Brothers Karamazov — Fyodor Dostoevsky | 1,982,184 |
| 2413 | Madame Bovary — Gustave Flaubert | 661,777 |
| 4300 | Ulysses — James Joyce | 1,566,711 |
| 2814 | Dubliners — James Joyce | 405,520 |
| 25344 | The Scarlet Letter — Nathaniel Hawthorne | 497,782 |
| 76 | Adventures of Huckleberry Finn — Mark Twain | 590,757 |
| 74 | The Adventures of Tom Sawyer — Mark Twain | 405,783 |
| 11 | Alice's Adventures in Wonderland — Lewis Carroll | 151,191 |
| 345 | Dracula — Bram Stoker | 870,683 |
| 84 | Frankenstein — Mary Shelley | 421,633 |
| 174 | The Picture of Dorian Gray — Oscar Wilde | 446,090 |
| 219 | Heart of Darkness — Joseph Conrad | 214,041 |
| 35 | The Time Machine — H. G. Wells | 181,575 |
| 36 | The War of the Worlds — H. G. Wells | 340,601 |
| 43 | The Strange Case of Dr Jekyll and Mr Hyde — R. L. Stevenson | 141,171 |
| 120 | Treasure Island — R. L. Stevenson | 372,720 |
| 82 | Ivanhoe — Walter Scott | 1,167,302 |
| 940 | The Last of the Mohicans — James Fenimore Cooper | 871,698 |
| 46 | A Christmas Carol — Charles Dickens | 181,890 |
| 730 | Oliver Twist — Charles Dickens | 917,357 |
| 967 | Nicholas Nickleby — Charles Dickens | 1,894,246 |
| 883 | Our Mutual Friend — Charles Dickens | 1,904,511 |
| 580 | The Pickwick Papers — Charles Dickens | 1,798,790 |
| 599 | Vanity Fair — William Makepeace Thackeray | 1,746,170 |
| 6688 | The Mill on the Floss — George Eliot | 1,212,210 |
| 507 | Adam Bede — George Eliot | 1,228,071 |
| 550 | Silas Marner — George Eliot | 402,656 |
| 122 | The Return of the Native — Thomas Hardy | 819,250 |
| 110 | Tess of the d'Urbervilles — Thomas Hardy | 875,702 |
| 107 | Far from the Madding Crowd — Thomas Hardy | 810,679 |
| 1432 | The Mayor of Casterbridge — Thomas Hardy | 301,923 |
| 160 | The Awakening — Kate Chopin | 365,734 |
| 203 | Uncle Tom's Cabin — Harriet Beecher Stowe | 1,059,743 |
| 514 | Little Women — Louisa May Alcott | 1,030,972 |
| 1837 | The Prince and the Pauper — Mark Twain | 431,701 |
| 86 | A Connecticut Yankee in King Arthur's Court — Mark Twain | 648,733 |
| 3176 | The Innocents Abroad — Mark Twain | 1,129,661 |
| 1497 | The Republic — Plato | 1,199,947 |
| 2680 | Meditations — Marcus Aurelius | 398,825 |
| 132 | The Art of War — Sun Tzu | 315,648 |
| 4363 | Beyond Good and Evil — Friedrich Nietzsche | 382,873 |
| 1228 | On the Origin of Species — Charles Darwin | 934,592 |
| 3300 | The Wealth of Nations — Adam Smith | 2,449,096 |
| 1404 | The Federalist Papers — Hamilton, Madison & Jay | 1,167,078 |
| 2376 | Up From Slavery — Booker T. Washington | 429,448 |
| 205 | Walden — Henry David Thoreau | 637,939 |
| 1322 | Leaves of Grass — Walt Whitman | 760,829 |
| 100 | The Complete Works of William Shakespeare | 5,422,721 |
| 26 | Paradise Lost — John Milton | 461,083 |

## 2. WikiText-103 — CC BY-SA 3.0

- **License:** the text is extracted from Wikipedia's verified Good and Featured
  articles; © Wikipedia contributors, **Creative Commons Attribution-ShareAlike
  3.0 (CC BY-SA 3.0)** — the HuggingFace dataset record (`Salesforce/wikitext`) is
  tagged `license:cc-by-sa-3.0` and `license:gfdl`. Dataset paper: Merity et al.,
  *Pointer Sentinel Mixture Models*, 2016 (arXiv:1609.07843).
- **Distribution used:** the official HuggingFace dataset `Salesforce/wikitext`,
  config `wikitext-103-raw-v1`, revision `b08601e04326c79dfdd32d625aee71d232d685c3`
  (parquet shards in `raw/wikitext/hf/`, converted back to the canonical
  `wiki.*.raw` line layout by `raw/wikitext/fetch_wikitext.sh`). The dataset's
  original host (Meta's `research.metamind.io` S3) now returns `AccessDenied` for
  the zip; the HuggingFace record above is its live official distribution.
- **Acquired:** train 541,096,899 bytes / 1,801,350 lines; validation 1,148,008
  bytes; test 1,292,014 bytes — 543,536,921 bytes total, in
  `raw/wikitext/wikitext-103-raw-v1/`.

## 3. Tokenizer (not text, for the record)

Tokenization uses the hive's shared BPE tokenizer (vocab 4,096) — the same data
file v1 and v2 were built with, read from the audit copy. Format is identical to
v1/v2: BOS (id 1) + BPE ids per line, uint16 stream, so v3 drops into the lab's
existing runners wherever a corpus file is pointed at them.
