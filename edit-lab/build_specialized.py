"""Build the SPECIALIZED retrain datasets (edit-lab, 2026-11-08).

Coordinator: target the one systematic defect - plans must land in the
3-7 step band. Composition:
  - every original >=3-step example x2          (38 rows)
  - 14 composed 4-5 step expansions of original 2-step tasks, written in
    the data's own step style (split compound steps into atomic ones,
    gold-style needs/done_when)                   (14 rows)
  - 2 genuinely-2-step guard examples x2 as regulariser (newsletter
    refusal, delete-files ask-first)              (4 rows)
  Total 56 rows, ~93% in the 3-7 band.

Researcher: gentle extraction emphasis with plan protection:
  - all 43 extract rows x2 (all outputs verified valid JSON)
  - all 28 plan rows x1
  Total 114 rows; trained 1 epoch at lr 1e-4 (vs original 3 epochs
  at 2e-4, loss 0.87 -> 0.06, which looped).
"""
import json, collections, pathlib

SRC = pathlib.Path.home() / "workspace/hivemind-muse/training/data"
OUT = pathlib.Path.home() / "workspace/edit-lab/data"
OUT.mkdir(parents=True, exist_ok=True)


def S(i, agent, task, needs, dw, fe=None):
    return {"id": f"s{i}", "agent": agent, "task": task,
            "needs": needs, "for_each": fe, "done_when": dw}


# Composed expansions: original row index -> new step list (gold style).
EXPANSIONS = {
    0: [S(1, "researcher", "Search huggingface for sentence embedding models and list the 10 most downloaded model ids", [], "10 model ids listed with download counts"),
        S(2, "browser", "Open https://huggingface.co/{item} and read the parameter size and license shown on the model page", ["s1"], "size and license read for each of the 10 models", "s1"),
        S(3, "coder", "From the sizes and licenses found, keep the 5 most downloaded models and sort them by downloads", ["s2"], "5 models ranked by downloads with size and license"),
        S(4, "researcher", "Check the 5 ranked models against the huggingface search listing to confirm the order", ["s3"], "ranking confirmed or corrected against the listing"),
        S(5, "writer", "Write a short ranked table of the 5 embedding models with size and license", ["s4"], "table lists all 5 models with sources")],
    2: [S(1, "coder", "Fetch the Open-Meteo hourly temperature forecast for Bengaluru (lat 12.97, lon 77.59) for today and save it as JSON", [], "forecast JSON saved with 24 hourly values"),
        S(2, "coder", "Plot the hourly temperatures from the saved forecast to a PNG chart", ["s1"], "chart PNG exists and is non-empty"),
        S(3, "coder", "Print the day's minimum and maximum temperature from the forecast", ["s1"], "min and max values printed"),
        S(4, "writer", "Tell Arnav where the chart is and the day's min and max temperature", ["s2", "s3"], "message gives the chart path and both temperatures")],
    3: [S(1, "researcher", "Look up the django package on pypi: the latest version", [], "latest django version quoted from pypi"),
        S(2, "researcher", "Look up the django package on pypi: the Python versions the latest release requires", [], "required Python quoted from pypi"),
        S(3, "researcher", "Look up the django 4.2 series in the Django docs: its support status and end of support", [], "4.2 support status quoted from the source"),
        S(4, "writer", "Compare 4.2.0 with the latest django version and say whether to upgrade", ["s1", "s2", "s3"], "comparison states both versions, the Python requirement and a clear upgrade verdict")],
    5: [S(1, "researcher", "Search arxiv for quantization of small language models and list the 8 most relevant recent papers with dates", [], "8 candidate papers with titles, links and dates"),
        S(2, "researcher", "Read the abstracts of the candidate papers and note each paper's method and models used", ["s1"], "one-line method note for each candidate"),
        S(3, "researcher", "Pick the 3 most relevant recent papers from the candidates", ["s2"], "3 papers chosen with a reason for each"),
        S(4, "writer", "Write a reading list: title, link and one-line summary for each paper", ["s3"], "reading list has all 3 papers with links")],
    6: [S(1, "coder", "Write a benchmark script that times list.sort() and sorted() on the same 1,000,000 random integers, 5 runs each", [], "script exists and runs without errors"),
        S(2, "coder", "Run the benchmark and print the 5 times for each method", ["s1"], "10 timing values printed"),
        S(3, "coder", "Run the benchmark again with a different random seed and print both runs' averages", ["s2"], "average times for both seeds printed"),
        S(4, "writer", "Report which is faster and by how much, with the measured numbers", ["s3"], "report quotes the measured averages from both runs")],
    10: [S(1, "coder", "Call https://huggingface.co/api/models?pipeline_tag=text-generation&sort=downloads&limit=10 and save the JSON", [], "JSON saved with 10 models and download counts"),
         S(2, "coder", "Make a bar chart PNG of the 10 models' download counts from the saved JSON", ["s1"], "chart PNG exists and is non-empty"),
         S(3, "coder", "Print the 10 models ranked by downloads", ["s1"], "ranked list of 10 printed"),
         S(4, "writer", "Show the top 10 list and point to the chart", ["s2", "s3"], "message lists all 10 and gives the chart path")],
    11: [S(1, "researcher", "Read https://en.wikipedia.org/wiki/Raspberry_Pi and list every model named in the article", [], "model names listed from the article"),
         S(2, "researcher", "From the article, extract each model's release year", ["s1"], "a year quoted for each model"),
         S(3, "coder", "Sort the models by release year and print them as a dated list", ["s2"], "chronological list printed with no duplicates"),
         S(4, "writer", "Write a dated timeline of Raspberry Pi models", ["s3"], "timeline covers every model with its year")],
    13: [S(1, "coder", "Fetch the Open-Meteo daily forecast for Delhi (lat 28.61, lon 77.21) for the next 7 days: max temp and rain", [], "7 days of daily forecast printed"),
         S(2, "coder", "Fetch the Open-Meteo hourly forecast for Delhi for Saturday and Sunday", ["s1"], "hourly values for both weekend days printed"),
         S(3, "coder", "Pick the weekend morning window with the lowest temperature and no rain", ["s2"], "one day and time window chosen with its temperature"),
         S(4, "writer", "Recommend the better day and time for an outdoor run based on the forecast", ["s3"], "recommendation names the day, time and expected temperature")],
    16: [S(1, "coder", "Write is_valid_pan(s) in Python for the format 5 letters, 4 digits, 1 letter", [], "function written and importable"),
         S(2, "coder", "Write 8 assert tests for is_valid_pan: valid PANs, wrong lengths, digits in letter positions, lowercase", ["s1"], "test file exists with 8 asserts"),
         S(3, "coder", "Run the tests and fix the function until all 8 pass", ["s2"], "all 8 tests pass"),
         S(4, "coder", "Add edge-case tests for empty and non-string inputs and run the full suite again", ["s3"], "full suite passes including edge cases"),
         S(5, "writer", "Give Arnav the function and what the tests cover", ["s4"], "message includes the function and the test coverage")],
    18: [S(1, "browser", "Open https://docs.python.org/3/ and read the latest Python version shown", [], "latest version number read from the page"),
         S(2, "browser", "Open the 'What's new' page for the latest version and read the main sections", ["s1"], "What's new page for that version opened"),
         S(3, "researcher", "Extract the release highlights from the What's new page: new features and deprecations", ["s2"], "highlights listed with quotes from the page"),
         S(4, "writer", "Summarize the release highlights in a short list", ["s3"], "summary lists the main changes for the version")],
    21: [S(1, "coder", "Fetch https://export.arxiv.org/api/query?search_query=cat:cs.CL&sortBy=submittedDate&max_results=30 and save the titles", [], "30 paper titles saved"),
         S(2, "coder", "Tokenize the titles, lowercase them and count word frequencies, dropping stopwords", ["s1"], "word counts computed for all titles"),
         S(3, "coder", "Print the 15 most common title words with counts", ["s2"], "ranked word list printed"),
         S(4, "writer", "Report the most common title words and what that suggests about current topics", ["s3"], "report quotes the top words and counts")],
    23: [S(1, "researcher", "Read https://en.wikipedia.org/wiki/Vector_database and note its definition", [], "definition quoted from the article"),
         S(2, "researcher", "From the article, list the named vector database products and which are open source", ["s1"], "products listed with open-source status"),
         S(3, "researcher", "For three open-source examples, note what each one is in one line", ["s2"], "three examples with one-line notes"),
         S(4, "writer", "Explain vector databases in plain words and list three open-source examples", ["s3"], "explanation is plain-language and names the three examples")],
    28: [S(1, "coder", "Fetch https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=10", [], "10 stories returned with title, url and points"),
         S(2, "coder", "Save the 10 stories to a JSON file with title, url and points", ["s1"], "JSON file exists with 10 entries"),
         S(3, "coder", "Re-open the saved JSON and verify it has 10 stories each with points", ["s2"], "verification prints 10 complete entries"),
         S(4, "writer", "Show the 10 stories with points", ["s3"], "all 10 stories shown with points and the file path")],
    30: [S(1, "coder", "Download https://quotes.toscrape.com/ and collect every link on the page", [], "link list saved with a count"),
         S(2, "coder", "Request each link with a 10 second timeout and record its status code", ["s1"], "status recorded for every link"),
         S(3, "coder", "Save the broken links (status 400 or more, or timeout) to a file", ["s2"], "broken-links file exists, possibly empty"),
         S(4, "writer", "Report how many links were checked and which are broken", ["s3"], "report gives the checked count and the broken list")],
}
REGULARISER = [25, 32]  # genuinely-2-step guard examples

rows = [json.loads(l) for l in open(SRC / "coordinator.jsonl")]
out = []
for i, r in enumerate(rows):
    n = len(json.loads(r["output"])["steps"])
    if n >= 3:
        out += [r, r]
    elif i in EXPANSIONS:
        nr = {"messages": r["messages"],
              "output": json.dumps({"steps": EXPANSIONS[i]})}
        out.append(nr)
    elif i in REGULARISER:
        out += [r, r]
    # remaining 2-step originals are dropped (the defect's source)
with open(OUT / "coordinator_specialized.jsonl", "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
dist = collections.Counter(len(json.loads(r["output"])["steps"]) for r in out)
print("coordinator_specialized:", len(out), "rows; step dist:", dict(dist))

ex = [json.loads(l) for l in open(SRC / "researcher_extract.jsonl")]
pl = [json.loads(l) for l in open(SRC / "researcher_plan.jsonl")]
rout = ex + ex + pl
with open(OUT / "researcher_specialized.jsonl", "w") as f:
    for r in rout:
        f.write(json.dumps(r) + "\n")
print("researcher_specialized:", len(rout), "rows (extract x2 =", 2 * len(ex),
      ", plan x1 =", len(pl), ")")
