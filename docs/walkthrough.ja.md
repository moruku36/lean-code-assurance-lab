# 最初の証明を読む

[English](walkthrough.md) · [ホーム](../README.ja.md) · [全体設計](architecture.ja.md)

1. [Leanモデル](../Reservation.lean)を開きます。`Nat` は0以上の整数、`Option Nat` は新しい予約数（`some next`）か拒否（`none`）を表します。まず各 `theorem` の型を読み、何を仮定して何を結論にするかを確かめます。
2. 定員10、予約済み7、追加3を当てはめます。`accept_if_fits` から答えはちょうど10です。追加を4に変えると `reject_if_exceeds` から拒否になります。`accepted_within_capacity` は任意の受理結果を出発点に、定員以下であることを示します。
3. ルートで `python scripts/check.py` を実行します。Leanだけ試すなら、`lake build` の後に `lake env lean Audit.lean` を実行します。[公理の検査](../Audit.lean)では、各定理が何を前提として使ったかをLeanに問い合わせます。定理の出力が欠ける場合や、許可した範囲外の公理に依存する場合は検証が止まります。
4. 出力JSONの `matching_rows` と `negative_control` を読みます。入力は各成分が0～7の全組み合わせと、大きな整数の境界6例です。[初回の成功ログ](https://github.com/moruku36/lean-code-assurance-lab/actions/runs/45159429077)では各言語で518件が一致し、比較演算子を一つ変えた対照では40件が不一致でした。最初の反例は `(0,0,0)`。追加0は収まるので、正しい答えは0です。
5. 手元だけで[Python実装](../examples/reservation/reserve.py)の `request > remaining` を `request >= remaining` に変えて再実行してください。Leanの証明は引き続き通り、Pythonとの照合は反例を示して止まります。演算子を戻すと元の結果を再現できます。

レビューには定理名、試した入力、対象の版を添えます。ビルドや実行環境で止まった場合は未判定と記録します。
