# Homology-group provenance

The released partitions preserve the union of inherited parent components and qualifying newly detected links. The search policy is identity ≥30%, coverage ≥80% in both directions and E-value ≤0.001. Parent sequences can bridge labelled proteins without becoming additional training examples.

The earlier graph omitted qualifying connections across some development folds and the internal-test boundary. The correction retained every original internal-test protein and moved newly connected development proteins into the test side. Internal test expanded from 2,822 to 2,841; development became 11,664. Development folds and neural-monitor splits were regenerated with seed 37, followed by the full registered 340-configuration search. These final partitions and results are the ones distributed with the resource.

The graph policy, detected-hit audits and revision records remain in `results/graph/` and `config/`. Original source filenames, internal revision identifiers and hashes are retained in technical provenance rather than renamed. The search was heuristic; no claim of exhaustively excluding all possible homologous relationships is made.

H3 uncertainty groups union inherited H3 components with the final parent components by sequence hash, without splitting inherited components. They are used for uncertainty only, not to assign training partitions. See `config/H3_group_policy.json`.
