# Lean4Agent: from a workflow specification to evidence of execution

[English home](../README.md) · [日本語](#日本語) · [Reading list](sources.md)

**Source**: Ruida Wang, Jerry Huang, Pengcheng Wang, Xuanqing Liu, Luyang Kong and Tong Zhang, *Lean4Agent: Formal Modeling and Verification for Agent Workflow and Trajectory*, [arXiv:2606.06523v3](https://arxiv.org/abs/2606.06523v3), especially §§2.2–2.3 and Appendix F. [Authors' implementation](https://github.com/RickySkywalker/Lean4Agent).

The paper distinguishes three checks: whether a workflow is structurally valid, whether the preconditions and postconditions compose under stated assumptions about each step, and whether the recorded run meets those conditions. A static check does not establish that an LLM followed the instructions. The authors also describe LeanEvolve, which proposes revisions from localized failures. Appendix F notes that ambiguous requirements and incorrect predicate annotations can survive formal checks.

## How this lab uses the idea

| Layer | Review question | Lab evidence |
| --- | --- | --- |
| Structure | Did the checkpoint run take an allowed sequence of steps? | Check an explicit protocol and identify the first invalid transition. |
| Contract | Under what assumptions does the checkpoint resume correctly? | Keep the reviewed typed model, accepted axioms, and assumption about the same snapshot separate from what was observed on disk. |
| Trajectory | Did each implementation actually return the expected page and cursor? | Compare observed Python and TypeScript outputs with an independent expected result for a fixed public synthetic fixture. |

## Run it

From the repository root, with the existing pinned Lean toolchain, Python and Node.js:

```sh
python3 -B scripts/check_checkpoint_workflow.py
```

The default invocation uses the installed `lean`; set `LEAN` to its executable path if it is not on `PATH`. The command prints a JSON report. See the [checked-in example](../evidence/checkpoint-workflow.json), the [Lean contract](../CheckpointWorkflow.lean) and the [runner](../scripts/check_checkpoint_workflow.py). The reference run exercised one valid handoff (five rows over three pages) and five expected refusals: one structural fault, two missing contract conditions, and two disagreements in the actual Python/TypeScript trajectory. A receipt is emitted only for the valid fixture.

This is a local, opt-in workflow, not a port of FormalAgentLib or LeanEvolve. Keep the candidate and oracle independent; freeze the inputs before editing. If a step or assumption fails, show where it failed and have the maintainer decide what to change. A finite replay is not a universal proof about Python or TypeScript, and a Lean proof about the typed model does not cover concurrency, production adapters, or the behavior of an agent. Do not use the authors' benchmark results as expected gains for this lab.

## Three-language reservation pilot

The checkpoint example above tests one workflow. The reservation pilot uses the same three-layer idea for a single, shared contract across Python, TypeScript, and Rust:

1. Check the declared stages and the evidence each stage must produce.
2. Check the Lean model's acceptance and rejection rules, and report the axioms on which the claims depend.
3. Run all three implementations on the same fixture and compare each with the executable Lean oracle, not just with each other.

The common input domain here is three unsigned 64-bit integers. Lean uses mathematical natural numbers; Rust rejects an overflowing sum instead of wrapping. Such a sum is larger than any permitted capacity, so the model also rejects it. The existing arbitrary-precision Python/TypeScript examples remain separate. This pilot verifies the model and bounds the implementation claim to concrete runs. It does not translate Rust source into Lean or replace the planned Aeneas evaluation.

### Run the reservation pilot

With Lean 4.19.0, Python 3.10+, Node.js 24+ and `rustc` on the same machine, from the repository root:

```sh
python3 -B scripts/check_reservation_workflow.py
```

The normal command emits an all-local receipt only if all three implementations match. A missing compiler is inconclusive (exit 2, no receipt). For a lab where the toolchains live on different machines, `--capture-rust` records the Rust run and `--rust-evidence rust.json` checks that record against the exact input and source plus the Lean/Python/TypeScript runs. The latter is deliberately a distinct result (exit 3, no all-local receipt). Matching hashes bind the record to inputs and source; they do not independently authenticate a remote machine or prove how the record was produced.

In the measured split-host run, each implementation matched the Lean oracle on 141 cases, including five out-of-range sums whose inputs are in range. A separate Rust CLI probe refused an input value outside the common domain. An exact-fill refusal and an overflowing addition that wraps were deliberately injected and detected. Check the [split-host verification report](../evidence/reservation-workflow-split-host.json) and [missing-Rust control](../evidence/reservation-workflow-missing-rust.json). The default three-toolchain run was not measured on one machine in this lab.

## 日本語

[日本語ホーム](../README.ja.md) · [参考文献](sources.md)

[Lean4Agent論文 v3](https://arxiv.org/abs/2606.06523v3)は、「手順の構造は正しいか」「各工程が前提と事後条件を満たすと仮定すると、手順全体が成立するか」「実際の実行はその条件どおりだったか」を分けて確認します。LLMの指示文に形式的な条件を付けても、LLMがそのとおりに動いた証明にはなりません。付録Fでは、仕様に残る曖昧さや、条件の記述自体が誤る可能性にも触れています。

最初の例では、Python／TypeScriptのチェックポイント再開を扱います。許可された順序、同じスナップショットで再開するという前提、実装が返したページとカーソルが、独立に計算した期待値と合うかを別々に見ます。食い違ったときは最初の箇所を示し、ルール自体を変えるかは人が判断します。

### 再現する

既存のLean固定版、Python、Node.jsを用意し、リポジトリのルートで `python3 -B scripts/check_checkpoint_workflow.py` を実行します。[出力例](../evidence/checkpoint-workflow.json)では、正常な5行・3ページの引き継ぎを1件確認し、意図的に入れた異常5件を該当の段階で拒否しました。受領票は正常例にだけ発行されます。

FormalAgentLibやLeanEvolveは導入せず、固定の公開合成データで任意に実行する検証です。標準CI、未見比較の条件、実運用は変更しません。論文の改善率がこのラボでも得られるとみなさず、証明・有限の再生試験・未検証事項を区別します。
### 3言語の共通検証

予約の例では「実行手順」「Leanで検査した仕様」「3言語の実行結果」を分けます。3言語の結果がそろうだけでなく、すべてをLeanの実行可能な仕様と照合します。共通範囲は符号なし64ビット整数です。Rustで足し算が範囲を超える場合は拒否します。数学上の和はどの有効な定員より大きいので、Leanの仕様でも拒否になります。この試験は既存の任意精度の例を置き換えず、Rustのコード自体を証明したことにもなりません。

Lean 4.19.0、Python 3.10以上、Node.js 24以上、`rustc` を同じ環境に用意し、`python3 -B scripts/check_reservation_workflow.py` を実行します。通常モードでは3言語が同じマシンで一致した場合だけ受領票を出します。今回はLean・Python・TypeScriptをクラウドで、RustをMac miniで実行し、同じソースと入力の記録を照合したところ、各141件が一致しました。足し算のオーバーフローを5件確認し、満杯ちょうどを拒む対照と桁あふれで値が巻き戻る対照も検出しました。一台での一括実行は未確認です。二台の照合は通常モードの合格とは別に扱います。
