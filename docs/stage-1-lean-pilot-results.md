# Lean 4 as an additional reviewer tool: first held-out pilot

[日本語](#日本語) · [Research protocol](experiments.md)

**Result: no additional defects were found by adding Lean 4 in this pilot. Do not make Lean a default review step on this evidence.**

The question was whether an executable Lean specification and proof checker improve an agent's review, not whether one implementation language is better than another. Two fresh reviewer sessions using the same model and reasoning setting assessed the same six unseen revisions and initial tests. A could add and run ordinary tests; B could do that and also use Lean 4. An independent evaluator held the labels until both sets of judgments were frozen. The implementation under review was Python; the shared Python/TypeScript example in Stage 0 is not part of this comparison.

| Outcome (unit: revision) | A: ordinary tests | B: ordinary tests + Lean 4 |
| --- | ---: | ---: |
| Defective changes correctly rejected | 3/3 | 3/3 |
| Valid changes correctly accepted | 3/3 | 3/3 |
| False rejections / unresolved | 0 / 0 | 0 / 0 |
| Defects detected by this arm alone | 0 | 0 |

The initial tests passed all six revisions. Both arms found the same three defects by adding targeted checks. B used Lean to compute the expected outcome for its three counterexamples, but A independently found each defect. The Lean toolchain checked five specification theorems; the executable model also agreed with the independent reference on 24 public and 60 held-out input examples. Those agreement checks are not additional revisions, and the theorems about the specification do not prove the Python code correct.

Reviewers self-reported about 45 and 65 seconds (A and B respectively); independent timing, token use, and specification preparation costs were not available. This six-revision pilot does not estimate a general benefit or cost. The next study will use fresh cases for exact large-integer exchange between Python `int` and TypeScript `bigint`, and a separate ordering contract. Both arms will start with strong ordinary property tests. We will look for a replayable detection unique to the Lean arm, false rejections, and measured cost before considering wider use.

## 日本語

**初回の未見比較では、Lean 4を追加しても検出は増えませんでした。この結果だけで標準レビューには導入しません。**

比べたのは実装言語ではなく、レビューにLeanの実行可能な仕様と証明検査を加える効果です。同じモデル・推論設定の独立したセッションに、同じ未見の変更6件と初期テストを渡しました。Aは通常のテスト、Bは同じテストに加えてLeanを利用でき、両方とも追加テストを作れます。別の評価担当が両方の回答を固定するまで正解を伏せました。今回の対象実装はPythonで、Stage 0のPython／TypeScript共通例とは別の比較です。

| 判定（単位：変更） | A：通常テスト | B：通常テスト＋Lean 4 |
| --- | ---: | ---: |
| 欠陥のある変更を正しく拒否 | 3/3 | 3/3 |
| 正常な変更を正しく受理 | 3/3 | 3/3 |
| 誤拒否／未判定 | 0 / 0 | 0 / 0 |
| その条件だけで検出した欠陥 | 0 | 0 |

初期テストは6件とも通り、追加確認で両条件が同じ3件の欠陥を見つけました。Bは反例3件の期待値をLeanで計算できましたが、Aも独立にすべて検出しました。Leanは仕様の定理5件を検査し、実行可能な仕様は公開24件・未見60件の入力例で独立の期待値と一致しました。これは変更を追加で評価した件数ではなく、Python実装全体を証明したわけでもありません。

所要時間は自己申告でA約45秒、B約65秒。独立計測、トークン、仕様の準備費用は未計測です。6件から一般的な効果や費用までは判断できません。次は新しい事例で、Pythonの `int` とTypeScriptの `bigint` の間で大きな整数を正確にやり取りする仕様と、別の並び順仕様を試します。両条件に強いプロパティテストを与え、Leanだけで拾えた再現可能な不具合、誤拒否、実測コストを見て導入を判断します。
