# Scoring the ordinary G49 replies

The 12 questions are public integration cases. The intended decisions were fixed before fitting. We scored the content of the reply a person receives, separately from the model's internal label and whether the correct GGUF activated.

| Domain | Correct user-facing content |
| --- | --- |
| Python | Recommends the built-in `filter` for keeping matching records. A list comprehension can perform the task, but it does not name the built-in the user asked for. |
| Geometry | Identifies volume as the measure of the capacity or internal space. |
| Pure water | Identifies liquid as the equilibrium phase at 72 °C and one atmosphere. |
| Conversation | Gives the neighbor a usable expression of thanks on the open prompt, or chooses `thank` on the explicit prompt. |
| Machine learning | Identifies the validation split for choosing hyperparameters. |
| Hardware timing | Identifies a microsecond. In prose the abbreviation may be written µs, μs or us. The explicit choices use `us`. |

The separate format check for explicit choices accepts the requested label alone, ignoring capitalization, surrounding whitespace, terminal punctuation and simple Markdown emphasis. The open questions ask for a short reason, sentence, ready-to-send reply or abbreviation according to their wording. Each judgment names the raw receipt containing the reply and the model's observed adapter scales.
