# Sources and reading path

[English home](../README.md) · [日本語ホーム](../README.ja.md)

Start with the Lean tutorial to read a proof, then try the tic-tac-toe project to see how a Python implementation can disagree with an executable specification. For the research design, the Lean system paper, the LeanDojo paper and the Aeneas paper answer three different questions.

## Primary sources behind the design

| Design question | What the source contributes | Source |
| --- | --- | --- |
| Who checks an agent's proposed proof? | The Lean reference describes the kernel and how to inspect the assumptions of a theorem. This motivates the named claims and axiom checks in the runner. | [Lean project](https://lean-lang.org/) · [Language reference](https://lean-lang.org/doc/reference/latest/) · [Validating a Lean Proof](https://lean-lang.org/doc/reference/latest/ValidatingProofs/) |
| How should a newcomer learn Lean? | The authors work through propositions as types, quantifiers, tactics and induction. Sections 3–5 are a useful companion to the reservation example. | [Theorem Proving in Lean 4](https://lean-lang.org/theorem_proving_in_lean4/) · [Official installation guide](https://lean-lang.org/install/) |
| Why can the specification also run? | Leonardo de Moura and Sebastian Ullrich describe the combination of a theorem prover, functional programming language and compiler in Lean 4. Compiling the oracle introduces its own runtime assumptions. | [The Lean 4 Theorem Prover and Programming Language, CADE 2021](https://lean-lang.org/papers/lean4.pdf) |
| How can Lean help test Python code? | Kazunori Sato's worked example executes a Lean tic-tac-toe specification and compares Python game results using Hypothesis. This is the direct precedent for the lab's executable oracle. The lab starts with a deterministic corpus. | [Original repository](https://github.com/kazunori279/lean4-tictactoe-test) · [Author's Japanese slides](https://kazunori279.github.io/lean4-tictactoe-test/slides_ja.html#1) · [Hypothesis documentation](https://hypothesis.readthedocs.io/en/latest/) |
| What evidence exists for AI-assisted proof search? | Yang and colleagues report a Lean environment and experiments on retrieval-assisted theorem proving. Their unit of evaluation is a theorem. This lab adds a separate experiment at the level of a service change. | [LeanDojo, NeurIPS 2023](https://papers.nips.cc/paper/2023/hash/4441469427094f8873d0fecb0c4e1cee-Abstract-Datasets_and_Benchmarks.html) |
| How could a proof be linked more closely to Rust source? | Son Ho and Jonathan Protzenko describe functional translation for a supported Rust fragment. The project documents its Charon front end and Lean backend. Record versions, accepted constructs and unsupported effects in each pilot. | [Aeneas paper, ICFP 2022](https://arxiv.org/abs/2206.07185) · [Aeneas toolchain](https://github.com/AeneasVerif/aeneas) |
| How can we check an agent workflow without treating its plan as proof of execution? | Lean4Agent separates structural checks, contracts under explicit per-step assumptions, and checks of the observed run. See how this lab applies the distinction to checkpoint handoff. | [Lean4Agent, arXiv v3](https://arxiv.org/abs/2606.06523v3) · [Lab reading note](lean4agent.md) |

## The six references that started the lab

| Reference | How to read it |
| --- | --- |
| [Lean 4 + Python Differential Testing, Japanese slides](https://kazunori279.github.io/lean4-tictactoe-test/slides_ja.html#1) | An author's walkthrough with runnable companion code. The game is a convenient way to inspect a counterexample by hand. |
| [Lean language homepage](https://lean-lang.org/) | Official entry point to the language, manuals and installation. This lab's toolchain is pinned in [lean-toolchain](../lean-toolchain); manuals marked “latest” move over time. |
| [形式検証超入門, 株式会社AIアシュアランス](https://zenn.dev/ghostdrift/books/355456ce679c1c) | Japanese introduction framing proof, responsibility and the author's ADIC approach. Useful background for talking with reviewers about who owns a specification. |
| [なぜ今形式検証なのか, senna / NCDC](https://zenn.dev/ncdc/articles/dcec80b0c067b0) | Japanese commentary connecting agent workflows and formal verification. The published [pstack materials](https://github.com/cursor/plugins/tree/main/pstack) are a separate source for the workflow itself. |
| [AI時短ラボ, リーマン予想に関する動画](https://www.youtube.com/watch?v=6OFMjG48J_Q) | A starting point for the question of what a formal check certifies. The title and channel were identified from publisher metadata. The lab makes no mathematical claim from the video. |
| [All Code Is Slop (Except Mine), Lauren Tan](https://youtu.be/O_zcc6Xl12g) | Talk published by AI Engineer. Title and channel were checked; no transcript was used. A practitioner reference for the question that motivated the lab. |
