"""Phase 2 field coverage: registration of the expansion niches.

The map is PLAN.md section 15. This module registers the smallest
specialists for every niche on it, in coverage-priority order:
constructed behaviours from field.py / field2.py wherever the job is
enumerable or checkable, and model-bound specialists (registered with
their interface binding, in-development until the backends load —
PLAN section 14) wherever the job needs a model's judgement.

testing is a phase-1 niche: phase 2 EXTENDS it (test analysis +
the test-writer model role, whose binding existed since phase 1).
Every other niche here is new and gets its own micro-coordinator
from niches.build_swarm, like every niche.
"""
from . import field as F
from . import field2 as G
from . import interface
from .specialist import Specialist

# new niches, in growth order (PLAN section 15); "testing" predates them
FIELD_NICHES = ["reading", "linting", "refactoring", "documenting",
                "security", "performance", "data", "sql", "dependencies",
                "build", "vcs", "regex", "shell", "languages", "web",
                "translation"]


def register_field_niches(reg):
    """Register every phase-2 specialist into the registry."""

    def add(name, niche, job, fn=None, binding=None):
        return reg.add(Specialist(name, niche, job, fn=fn, binding=binding))

    def model(name, niche, job):
        return add(name, niche, job, binding=interface.BINDINGS[name])

    # ---- reading: understand existing code -------------------------------
    add("import-lister", "reading", "list the modules a program imports", F.import_lister)
    add("function-lister", "reading", "list every function/method defined", F.function_lister)
    add("class-lister", "reading", "list classes with their methods", F.class_lister)
    add("signature-extractor", "reading", "extract one function's signature", F.signature_extractor)
    add("docstring-extractor", "reading", "extract a module/function/class docstring", F.docstring_extractor)
    add("call-finder", "reading", "list the distinct callables a program calls", F.call_finder)
    add("branch-counter", "reading", "count decision points of a function/module", F.branch_counter)
    add("recursion-detector", "reading", "list functions that call themselves", F.recursion_detector)
    add("code-line-counter", "reading", "count code lines (non-blank, non-comment)", F.code_line_counter)
    model("code-explainer", "reading", "explain what a program does")

    # ---- testing (extension of the phase-1 niche) ------------------------
    add("test-function-counter", "testing", "count test functions in a test file", F.test_function_counter)
    add("assertion-counter", "testing", "count assertions in a test file", F.assertion_counter)
    add("untested-function-finder", "testing", "find public functions no test mentions", F.untested_function_finder)
    model("test-writer", "testing", "write tests for a function")

    # ---- linting: check-only, one check per specialist -------------------
    add("line-length-checker", "linting", "find lines over the length limit", F.line_length_checker)
    add("trailing-whitespace-checker", "linting", "find lines ending in whitespace", F.trailing_whitespace_checker)
    add("tab-indent-checker", "linting", "find tab-indented lines", F.tab_indent_checker)
    add("final-newline-checker", "linting", "check exactly one final newline", F.final_newline_checker)
    add("function-name-case-checker", "linting", "find non-snake-case function names", F.function_name_case_checker)
    add("constant-name-case-checker", "linting", "find module constants not UPPER_SNAKE", F.constant_name_case_checker)
    add("wildcard-import-checker", "linting", "find from-x-import-* statements", F.wildcard_import_checker)
    add("bare-except-checker", "linting", "find bare except clauses", F.bare_except_checker)
    add("print-call-checker", "linting", "find print() call sites", F.print_call_checker)

    # ---- refactoring: one smallest transform each ------------------------
    add("trailing-whitespace-stripper", "refactoring", "strip trailing whitespace", F.trailing_whitespace_stripper)
    add("tab-expander", "refactoring", "expand leading tabs to 4 spaces", F.tab_expander)
    add("final-newline-fixer", "refactoring", "normalize the final newline", F.final_newline_fixer)
    add("import-block-sorter", "refactoring", "sort the header import block", F.import_block_sorter)
    add("unused-import-remover", "refactoring", "remove provably unused imports", F.unused_import_remover)
    add("rename-symbol", "refactoring", "rename one identifier everywhere", F.rename_symbol)
    model("refactor-suggester", "refactoring", "suggest the next refactoring step")

    # ---- documenting ------------------------------------------------------
    add("docstring-coverage-checker", "documenting", "find definitions lacking docstrings", F.docstring_coverage_checker)
    add("todo-marker-finder", "documenting", "find TODO/FIXME/XXX/HACK markers", F.todo_marker_finder)
    add("license-header-checker", "documenting", "check for a license header", F.license_header_checker)
    add("comment-density-counter", "documenting", "measure the comment-line ratio", F.comment_density_counter)
    model("docstring-writer", "documenting", "write a docstring for a definition")

    # ---- security: one smell per finder ----------------------------------
    add("hardcoded-secret-finder", "security", "find string literals assigned to secret names", F.hardcoded_secret_finder)
    add("eval-exec-finder", "security", "find eval()/exec() calls", F.eval_exec_finder)
    add("pickle-load-finder", "security", "find pickle load/loads calls", F.pickle_load_finder)
    add("sql-interpolation-finder", "security", "find execute() fed interpolated SQL", F.sql_interpolation_finder)
    add("shell-true-finder", "security", "find shell=True calls", F.shell_true_finder)
    add("weak-hash-finder", "security", "find hashlib md5/sha1 calls", F.weak_hash_finder)

    # ---- performance: one smell per finder -------------------------------
    add("loop-depth-finder", "performance", "measure deepest loop nesting", F.loop_depth_finder)
    add("string-concat-in-loop-finder", "performance", "find += accumulation inside loops", F.string_concat_in_loop_finder)
    add("global-mutation-finder", "performance", "find functions using global", F.global_mutation_finder)

    # ---- data: formats, checked with the stdlib parsers ------------------
    add("json-validity-checker", "data", "check a text parses as JSON", G.json_validity_checker)
    add("json-key-lister", "data", "list a JSON object's top-level keys", G.json_key_lister)
    add("csv-shape-checker", "data", "check CSV rows match the header width", G.csv_shape_checker)
    add("csv-column-lister", "data", "list a CSV text's header row", G.csv_column_lister)
    add("toml-validity-checker", "data", "check a text parses as TOML", G.toml_validity_checker)

    # ---- sql --------------------------------------------------------------
    add("sql-statement-classifier", "sql", "classify a SQL statement by first keyword", G.sql_statement_classifier)
    add("sql-table-extractor", "sql", "extract FROM/JOIN table names", G.sql_table_extractor)
    add("sql-where-checker", "sql", "flag UPDATE/DELETE without WHERE", G.sql_where_checker)
    add("sql-keyword-caser", "sql", "uppercase SQL keywords", G.sql_keyword_caser)
    model("sql-writer", "sql", "write a SQL statement for a request")

    # ---- dependencies ------------------------------------------------------
    add("requirements-parser", "dependencies", "parse requirements text into name+spec", G.requirements_parser)
    add("unpinned-dependency-finder", "dependencies", "find requirements without an == pin", G.unpinned_dependency_finder)
    add("import-origin-classifier", "dependencies", "classify a module: stdlib/third-party/local", G.import_origin_classifier)
    add("version-satisfies-checker", "dependencies", "check a version against a spec", G.version_satisfies_checker)

    # ---- build -------------------------------------------------------------
    add("pyproject-field-checker", "build", "check pyproject project.name/version", G.pyproject_field_checker)
    add("dockerfile-instruction-lister", "build", "list a Dockerfile's instructions", G.dockerfile_instruction_lister)
    add("makefile-target-lister", "build", "list a Makefile's targets", G.makefile_target_lister)

    # ---- vcs: version-control text, never the repo -------------------------
    add("conflict-marker-finder", "vcs", "find merge-conflict markers in a text", G.conflict_marker_finder)
    add("diff-stat-counter", "vcs", "count added/removed lines of a diff", G.diff_stat_counter)
    add("conventional-commit-checker", "vcs", "check Conventional Commits format", G.conventional_commit_checker)
    model("commit-message-writer", "vcs", "write a commit message for a change")

    # ---- regex -------------------------------------------------------------
    add("regex-compile-checker", "regex", "check a pattern compiles", G.regex_compile_checker)
    add("regex-match-runner", "regex", "run a pattern over sample strings", G.regex_match_runner)
    add("nested-quantifier-finder", "regex", "find nested-quantifier shapes in a pattern", G.nested_quantifier_finder)

    # ---- shell ---------------------------------------------------------------
    add("bash-syntax-checker", "shell", "check a shell script's syntax (bash -n)", G.bash_syntax_checker)
    add("shebang-checker", "shell", "check a script's shebang line", G.shebang_checker)
    add("unquoted-variable-finder", "shell", "find unquoted $VAR expansions", G.unquoted_variable_finder)
    add("dangerous-rm-finder", "shell", "find rm -rf sites", G.dangerous_rm_finder)

    # ---- languages -------------------------------------------------------------
    add("language-identifier", "languages", "name a file's language (extension/shebang)", G.language_identifier)
    add("javascript-syntax-checker", "languages", "check JavaScript syntax (node --check)", G.javascript_syntax_checker)
    add("c-brace-balance-checker", "languages", "check bracket balance in C-like code", G.c_brace_balance_checker)
    model("shell-writer", "languages", "write a shell script for a request")

    # ---- web ---------------------------------------------------------------------
    add("html-tag-balance-checker", "web", "check HTML tags nest and close", G.html_tag_balance_checker)
    add("url-extractor", "web", "extract URLs from a text", G.url_extractor)
    model("api-usage-advisor", "web", "advise how to call an API correctly")

    # ---- translation: a model-bound niche (queued per PLAN section 14) ------------
    model("code-translator", "translation", "translate a snippet between two languages")
    return reg
