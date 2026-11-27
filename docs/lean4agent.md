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

## 日本語

[日本語ホーム](../README.ja.md) · [参考文献](sources.md)

[Lean4Agent論文 v3](https://arxiv.org/abs/2606.06523v3)は、「手順の構造は正しいか」「各工程が前提と事後条件を満たすと仮定すると、手順全体が成立するか」「実際の実行はその条件どおりだったか」を分けて確認します。LLMの指示文に形式的な条件を付けても、LLMがそのとおりに動いた証明にはなりません。付録Fでは、仕様に残る曖昧さや、条件の記述自体が誤る可能性にも触れています。

このラボでは、Python／TypeScriptのチェックポイント再開に絞ります。許可された順序、同じスナップショットで再開するという前提、実装が返したページとカーソルが、独立に計算した期待値と合うかを別々に見ます。食い違ったときは最初の箇所を示し、ルール自体を変えるかは人が判断します。

### 再現する

既存のLean固定版、Python、Node.jsを用意し、リポジトリのルートで `python3 -B scripts/check_checkpoint_workflow.py` を実行します。[出力例](../evidence/checkpoint-workflow.json)では、正常な5行・3ページの引き継ぎを1件確認し、意図的に入れた異常5件を該当の段階で拒否しました。受領票は正常例にだけ発行されます。

FormalAgentLibやLeanEvolveは導入せず、固定の公開合成データで任意に実行する検証です。標準CI、未見比較の条件、実運用は変更しません。論文の改善率がこのラボでも得られるとみなさず、証明・有限の再生試験・未検証事項を区別します。
