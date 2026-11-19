# Independent single-turn depot-fee panel B

Frozen case file SHA-256: `c08ce69148b1c74fceb586f7f64335b978e94f293579855928dd00780038a131`.

The case writer used the archived depot fee contract, whose input is a list of positive whole parcel weights in grams, with an empty list for an empty shipment. The positive cases ask for today's standard fee on one fully specified depot shipment. The negative cases require different work or more information. Case writing did not use another panel, implementation, probe results or adapter output. No case was changed after the first hash.

The file contains 30 fixed, independently written single-turn English requests. Fifteen can execute the saved method directly, including two empty shipments. Fifteen should take another path. The positive cases include requests with numbers in words, repeated weights, exact multiplicity, a list with the unit stated once, and an indirect budget question. The negatives include an exact total with unknown individual weights, an estimate, a fractional weight, an embedded quotation, an active request for different work, and a different shipping tariff.

Score the first routing decision per request. The oracle weights are in the order of mention with multiplicity preserved. An executed call on a positive case counts only if the list matches the oracle and the returned fee matches the saved depot convention on that list. Report positive completions, positive abstentions, incorrectly executed arguments, and calls on negative requests separately. A balanced set with a small number of hand-written examples measures performance on this panel, rather than deployment prevalence.
