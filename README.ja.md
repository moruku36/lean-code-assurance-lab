# Lean Code Assurance Lab

[English](README.md) · [全体設計](docs/architecture.ja.md) · [実験計画](docs/experiments.ja.md) · [参考文献](docs/sources.md)

AIが書いたコードをサービスに取り込むとき、どこまでなら根拠を持って信頼できるか。この研究では、Python・TypeScript・Rustのコードから一つの判断を取り出し、人が決めた仕様をAIエージェントがLeanで記述します。証明した性質と実際のコードの動作を、それぞれ追試できる形で残します。

## 最初の題材は予約の上限

定員が10、予約済みが7なら、3件の追加予約は受理して合計10を返し、4件なら拒否するのが仕様です。「定員を超えない」だけなら、全件を拒否するコードでも満たせます。そこで、**受理すべき条件と拒否すべき条件の両方**を書きました。

| 知りたいこと | 根拠を確認する場所 |
| --- | --- |
| どの自然数を入力しても、受理後の予約数は定員以下か | [Leanが検査する3つの定理](Reservation.lean)と[依存する公理の検査](Audit.lean) |
| Python・TypeScriptの実装も同じ答えを返すか | [各言語の実装](examples/reservation/)を[検証スクリプト](scripts/check.py)が各518入力で照合。満員ちょうどや大きな整数も含みます。 |
| 検証方法は境界条件の誤りに気づけるか | わざと「満員ちょうど」を拒否する実装を用意し、Leanの答えと食い違う入力を出力します。 |

```mermaid
flowchart TD
    C["人が確認した要件と入力範囲"] --> M["実行できるLean仕様"]
    M --> P["Leanが全入力について定理を検査"]
    M --> O["同じ仕様を固定入力で実行"]
    I["Python・TypeScriptの実装"] --> D["出力を照合"]
    O --> D
    P --> R["証明・具体例・前提を確認"]
    D --> R
```

## 自分で試す

Elanを含むLean環境、Python 3.10以上、Node.js 24以上を用意し、リポジトリのルートで次のコマンドを実行します。初回は固定版のLeanを取得することがあります。証明のビルド、公理の確認、2言語との照合が終わると、結果がJSONで表示されます。[Lean公式インストール手順](https://lean-lang.org/install/)

```sh
python scripts/check.py
```

Pythonのコマンド名が `python3` の環境では `python3 scripts/check.py` で実行できます。初回の公開実行では3定理が通り、両言語で各518件が一致し、境界を間違えた対照では40件の不一致が出ました。[記録したJSON](evidence/reservation-baseline.json)・[CIの実行履歴](https://github.com/moruku36/lean-code-assurance-lab/actions/workflows/assurance.yml)・[予約の例を読み解く手順](docs/walkthrough.ja.md)

## 自分のサービスへの進め方

| 対象 | このリポジトリでできること |
| --- | --- |
| Python・TypeScript | 両言語の予約例を実行できます。次は未使用の変更を使って、通常のテストとLeanを持たせたエージェントの検出力を比較します。[実験計画](docs/experiments.ja.md) |
| Rust | 固定長整数を使う小さな関数を選び、AeneasでLeanに変換する実験を計画しています。[変換時に確認する前提](docs/architecture.ja.md) |
| 既存サービス | 一つの判定関数とその版、入力の契約、匿名化した例を持ち込む手順があります。[エージェントへの指示](AGENTS.md) |

今回の証拠が届くのは、モデルに書いた性質と、照合した入力での実装の振る舞いまでです。APIでの入力変換、同時予約、保守性、サービス全体のセキュリティには別の検証が必要です。[保証範囲の読み方](docs/architecture.ja.md)
