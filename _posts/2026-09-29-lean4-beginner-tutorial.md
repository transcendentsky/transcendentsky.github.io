---
title: Lean 4 新手教程：从第一个程序到形式化证明
tags:
  - Lean 4
  - 形式化验证
  - 数学
  - 编程语言
---

> Lean 4 既是一门函数式编程语言，也是一套交互式定理证明器。它最值得学习的地方，不是某个神奇的自动化 tactic，而是让程序、命题和机器检查的证明处在同一个类型系统里。本文从安装和第一个文件开始，带你理解 `#check`、`#eval`、函数、命题、证明、tactic、归纳和常见报错，并给出一条适合新手的学习路线。

![Lean 4 beginner tutorial workflow](/assets/images/lean4-beginner-tutorial/lean4-proof-workflow.svg)

<!--more-->

## 一、Lean 4 是什么？

如果把 Python、Coq 和数学证明工具放在一起比较，Lean 4 同时覆盖了三类能力：

| 能力 | 说明 | 一个典型例子 |
| --- | --- | --- |
| 函数式编程 | 定义函数、数据类型、递归和模块 | `def double (n : Nat) := n + n` |
| 定理证明 | 声明命题，并构造可检查的证明 | `theorem add_zero ...` |
| 形式化验证 | 把程序性质写成类型或定理 | 证明排序函数输出有序 |

Lean 的基本思想可以概括为：

```text
命题是类型（Propositions are types）
证明是这个类型的一个值（Proofs are terms）
程序也是项（Programs are terms）
```

例如，命题 `P → Q` 可以看作一个函数类型：它接收一个 `P` 的证明，返回一个 `Q` 的证明。命题 `P ∧ Q` 则类似于一个同时包含 `P` 证明和 `Q` 证明的结构。

Lean 的 tactic 并不是“绕过证明”的黑箱。tactic 会操作当前 proof state，构造一个证明项，最后由 Lean kernel 检查这个证明项是否符合定理类型。这也是形式化证明和普通测试的重要区别：测试只能覆盖一些运行路径，而成功通过 kernel 检查的证明对应于类型系统中的完整证据。

## 二、安装 Lean 4

### 2.1 推荐方式：VS Code 加官方扩展

官方安装页推荐通过 VS Code 和 Lean 4 扩展开始。基本步骤如下：

1. 安装 [Visual Studio Code](https://code.visualstudio.com/)。
2. 在扩展市场安装官方的 [Lean 4 extension](https://marketplace.visualstudio.com/items?itemName=leanprover.lean4)。
3. 打开 Lean 扩展的文档或 Setup Guide，按照向导安装 `elan` 和对应的 Lean 工具链。
4. 重启 VS Code，新建一个 `.lean` 文件，观察右侧的 Infoview 是否正常显示。

`elan` 可以理解为 Lean 的版本管理器。实际项目通常会通过 `lean-toolchain` 固定版本，避免不同机器上的 Lean 版本不一致。不要在项目里只写“使用最新版 Lean”，因为一个小版本变化就可能影响语法、库接口和 tactic 行为。

### 2.2 用命令行确认环境

在终端中可以检查：

```bash
elan --version
lean --version
lake --version
```

其中：

- `lean` 是编译器和命令行解释器；
- `lake` 是 Lean 4 的构建工具和包管理入口；
- `elan` 负责安装和切换工具链。

如果命令不存在，优先回到官方 Setup Guide，而不是随便通过系统包管理器安装一个同名程序。不同发行版的软件源可能带来过旧版本，或者缺少项目所需的工具链配置。

## 三、第一个 Lean 文件

新建 `Main.lean`：

```lean
import Std

def double (n : Nat) : Nat := n + n

#check double
#check Nat
#eval double 21

def greeting (name : String) : String :=
  "Hello, " ++ name ++ "!"

#eval greeting "Lean"
```

这里出现了三个非常常用的命令：

| 命令 | 用途 |
| --- | --- |
| `#check expression` | 查看表达式的类型 |
| `#eval expression` | 对可计算表达式求值 |
| `#print name` | 查看定义、定理或类型的展开结果 |

在编辑器中把光标放到 `double` 或 `Nat` 上，Lean 还会显示悬浮信息。新手遇到报错时，第一反应应该是检查“我以为这个表达式是什么类型”，而不是立即尝试更多 tactic。

## 四、函数、类型和类型推断

Lean 是静态类型语言，但很多类型可以由上下文推断出来：

```lean
def square (n : Nat) := n * n

def compose (f : β → γ) (g : α → β) : α → γ :=
  fun x => f (g x)

#check square
#check compose
#check compose Nat.succ square
```

`α`、`β`、`γ` 是隐式的类型参数。Lean 会根据函数参数和返回值推断它们的关系。如果想显式写出参数，可以这样：

```lean
def identity (α : Type) (x : α) : α := x

#check identity Nat 3
#check identity String "hello"
```

函数类型 `α → β` 表示从 `α` 到 `β` 的函数。多参数函数本质上是柯里化函数：

```lean
def add (a : Nat) (b : Nat) : Nat := a + b

#check add       -- Nat → Nat → Nat
#check add 1     -- Nat → Nat
#eval add 1 2
```

这和 Python 里“传入两个参数”的表面写法不同。理解函数类型是进入 Lean 的第一个关键台阶。

## 五、从 `example` 开始写证明

Lean 中最适合练习的小定理是 `example`。它会被检查，但不会要求你给它一个长期使用的名字：

```lean
example (a b : Nat) : a + b = b + a := by
  exact Nat.add_comm a b
```

如果希望以后引用它，就写成 `theorem`：

```lean
theorem add_comm_example (a b : Nat) : a + b = b + a := by
  exact Nat.add_comm a b
```

`exact` 的含义是：当前目标已经有一个完全匹配的证明项。这里 `Nat.add_comm a b` 的类型正好是 `a + b = b + a`。

还可以使用 term-style 写法：

```lean
theorem add_comm_term (a b : Nat) : a + b = b + a :=
  Nat.add_comm a b
```

或者用 `by` 进入 tactic-style：

```lean
theorem add_comm_tactic (a b : Nat) : a + b = b + a := by
  simpa using Nat.add_comm a b
```

新手可以先用 `by`，因为它能把复杂证明拆成多个小步骤；当定理已经稳定时，再考虑是否用更紧凑的 term-style 表达。

## 六、理解 proof state

看下面的定理：

```lean
theorem implication_identity (p : Prop) : p → p := by
  intro hp
  exact hp
```

执行 `intro hp` 之后，目标从：

```text
⊢ p → p
```

变成：

```text
hp : p
⊢ p
```

这就是 proof state：上面是局部上下文，下面是当前还需要构造的目标。`intro` 把函数参数或蕴含前件引入上下文；`exact hp` 用已有的假设完成目标。

再看合取：

```lean
theorem and_swap (p q : Prop) : p ∧ q → q ∧ p := by
  intro hpq
  constructor
  · exact hpq.right
  · exact hpq.left
```

`constructor` 会按照目标类型的构造器拆开目标。目标是 `q ∧ p` 时，它生成两个子目标：先证明 `q`，再证明 `p`。圆点 `·` 用来分别进入两个子目标。

## 七、最常用的基础 tactic

### 7.1 `intro`、`exact` 和 `assumption`

```lean
theorem use_assumption (p q : Prop) : p → q → p := by
  intro hp hq
  assumption
```

`assumption` 会在当前上下文里寻找与目标类型匹配的假设。上面的 `hq` 没有被使用，这是允许的，但大型项目中可以考虑重命名或调整定理结构，让证明更易读。

### 7.2 `apply`

`apply` 从目标反向使用一个定理：

```lean
theorem trans_example (a b c : Nat)
    (hab : a = b) (hbc : b = c) : a = c := by
  apply Eq.trans hab
  exact hbc
```

如果一个定理的结论能匹配当前目标，`apply` 会把它的前提变成新的子目标。它适合使用已有 lemma，但在目标复杂时，先用 `#check` 确认定理的完整类型。

### 7.3 `rfl`

当等式两边经过定义展开后相同，可以用 `rfl`：

```lean
def triple (n : Nat) : Nat := n + n + n

example (n : Nat) : triple n = n + n + n := by
  rfl
```

`rfl` 不是“尝试计算后碰巧相等”，而是使用等式自反性和定义展开后的 definitional equality。若两边需要使用某个数学定理才能相等，`rfl` 通常不会成功。

### 7.4 `simp`

`simp` 使用一组简化规则重写目标：

```lean
example (n : Nat) : n + 0 = n := by
  simp

example (p q : Prop) (hp : p) (hq : q) : p ∧ q := by
  simp [hp, hq]
```

不要把 `simp` 当作万能搜索器。它擅长规范化表达式、使用标记为 simp 的 lemma、清理单位元和明显的逻辑结构；当证明需要真正的算法思路时，应先手工拆分目标。

### 7.5 `rw` 和 `calc`

`rw` 按照等式进行重写：

```lean
example (a b c : Nat) (h : a = b) : a + c = b + c := by
  rw [h]
```

`calc` 适合写成接近数学推导的形式：

```lean
example (a b c : Nat) (hab : a = b) (hbc : b = c) : a = c := by
  calc
    a = b := hab
    _ = c := hbc
```

在团队代码中，`calc` 往往比连续多次 `rw` 更容易维护，因为每一步的中间表达式和使用的 lemma 都清楚可见。

### 7.6 `norm_num`、`omega` 和 `linarith`

这些自动化 tactic 通常来自数学库环境，而不是最小的 `Std` 导入。它们的分工大致是：

| tactic | 典型用途 |
| --- | --- |
| `norm_num` | 化简具体数字运算和数值不等式 |
| `omega` | Presburger 算术，如自然数和整数上的线性关系 |
| `linarith` | 线性算术不等式，常用于实数或有序环 |
| `ring` | 多项式恒等式归一化 |
| `aesop` | 基于规则和局部假设进行结构化搜索 |

例如，在安装并导入 mathlib 的项目中，可以写：

```lean
import Mathlib

example (x y : ℤ) (h₁ : x ≤ y) (h₂ : y ≤ x) : x = y := by
  omega

example (x y : ℚ) : (x + y)^2 = x^2 + 2*x*y + y^2 := by
  ring
```

学习这些 tactic 的正确方式是先知道它们解决哪类目标，再用 `#check`、文档和最小例子确认适用范围，而不是把所有失败都归因于“Lean 太严格”。

## 八、命题逻辑的基本证明模式

### 8.1 蕴含：先引入前提

```lean
theorem modus_ponens (p q : Prop) : (p → q) → p → q := by
  intro hpq hp
  exact hpq hp
```

### 8.2 合取：拆开或构造

```lean
theorem and_intro_example (p q : Prop) : p → q → p ∧ q := by
  intro hp hq
  exact And.intro hp hq
```

也可以使用 tactic：

```lean
theorem and_intro_example' (p q : Prop) : p → q → p ∧ q := by
  intro hp hq
  constructor
  · exact hp
  · exact hq
```

### 8.3 析取：选择一个分支

```lean
theorem or_left (p q : Prop) : p → p ∨ q := by
  intro hp
  exact Or.inl hp

theorem or_cases (p q r : Prop) : (p → r) → (q → r) → p ∨ q → r := by
  intro hpr hqr hpq
  cases hpq with
  | inl hp => exact hpr hp
  | inr hq => exact hqr hq
```

`cases` 会按照归纳类型或逻辑构造的所有可能形状拆分情况。对 `p ∨ q`，有 `inl` 和 `inr` 两种情况。

### 8.4 全称和存在

```lean
theorem forall_example : ∀ n : Nat, n = n := by
  intro n
  rfl

theorem exists_example : ∃ n : Nat, n = 3 := by
  exact ⟨3, rfl⟩
```

证明 `∀ n, P n` 时，引入任意的 `n`；证明 `∃ n, P n` 时，需要给出一个具体 witness 和它满足性质的证明。

## 九、归纳：证明递归数据结构的性质

自然数是最适合学习归纳的例子：

```lean
theorem zero_add (n : Nat) : 0 + n = n := by
  induction n with
  | zero =>
      rfl
  | succ n ih =>
      simp [Nat.add_succ, ih]
```

`induction n` 生成两种情况：

- `zero`：证明基例；
- `succ n`：假设归纳假设 `ih`，证明后继情况。

归纳的思维模式是：

```text
要证明所有 n 都成立
    -> 证明最小情况
    -> 假设 n 成立
    -> 用这个假设证明 n+1 成立
```

对列表也一样：

```lean
def lengthNat : List α → Nat
  | [] => 0
  | _ :: xs => lengthNat xs + 1

theorem lengthNat_cons (x : α) (xs : List α) :
    lengthNat (x :: xs) = lengthNat xs + 1 := by
  rfl
```

实际项目中，最常见的困难不是 `induction` 关键字本身，而是归纳假设的形式不够强、递归定义方向和目标方向不一致，或者需要先使用 `generalizing` 把变量重新泛化。

## 十、自己定义数据类型和函数

Lean 的证明能力和编程能力来自同一个类型系统。可以定义一个简单的二叉树：

```lean
inductive Tree (α : Type) where
  | leaf : α → Tree α
  | node : Tree α → Tree α → Tree α

def count : Tree α → Nat
  | .leaf _ => 1
  | .node left right => count left + count right

example (x y : α) : count (.node (.leaf x) (.leaf y)) = 2 := by
  rfl
```

这个例子展示了 Lean 的 pattern matching。定义 `count` 时覆盖了 `Tree` 的所有构造器；之后，许多关于树的性质都可以通过对树做结构归纳来证明。

在更大的项目中，建议把“数据类型定义”“可执行函数”“规范定理”“测试例子”分开组织。这样既方便程序运行，也方便后续证明和重构。

## 十一、Lean 项目的基本结构

一个简单项目通常包含：

```text
MyProject/
├── lakefile.toml
├── lean-toolchain
├── MyProject/
│   └── Basic.lean
└── Main.lean
```

常用命令：

```bash
lake new MyProject
cd MyProject
lake build
lake env lean MyProject/Basic.lean
```

不同版本的 Lake 模板和依赖配置可能略有差异，因此建议以你当前工具链生成的项目模板为准。对于 mathlib 项目，不要手工复制大量库文件，而是使用项目的依赖声明和 Lake 管理依赖版本。

一个适合练习的 `Main.lean` 可以是：

```lean
import MyProject.Basic

theorem demo (n : Nat) : n + 0 = n := by
  simp
```

`lake build` 成功后，才说明项目中的导入路径、依赖、版本和所有 Lean 文件能够共同编译。只在编辑器里看到局部绿色提示，不等于整个项目构建成功。

## 十二、如何读懂错误信息

### 12.1 类型不匹配

```lean
def bad : Nat := "hello"
```

报错的本质是：字符串不是自然数。先看错误中的 expected 和 got：

```text
expected: Nat
got: String
```

### 12.2 找不到名称

```lean
example : 1 + 1 = 2 := by
  exact add_comm 1 1
```

如果 Lean 找不到 `add_comm`，可能是名字需要限定为 `Nat.add_comm`，也可能是当前导入没有提供对应 lemma。用 `#check Nat.add_comm` 验证名称和类型。

### 12.3 tactic 没有解决目标

```lean
example (a b : Nat) : a + b = b + a := by
  rfl
```

这里 `rfl` 通常不够，因为交换律不是定义展开后自动相同，而是一个数学定理。改为：

```lean
example (a b : Nat) : a + b = b + a := by
  exact Nat.add_comm a b
```

### 12.4 不要长期依赖 `sorry`

`sorry` 可以让 Lean 暂时接受一个未完成证明，适合搭建文件结构或先写定理接口，但它不代表定理已经被证明。提交代码前，应该搜索并清理 `sorry`，或者明确把它列入待办和构建策略。

## 十三、一个适合新手的练习顺序

建议按下面顺序练习，每一步都让 Lean 编译通过：

| 阶段 | 练习内容 | 目标 |
| --- | --- | --- |
| 1 | `def`、函数参数、`#check`、`#eval` | 熟悉类型和表达式 |
| 2 | `example`、`theorem`、`exact`、`rfl` | 写出最小证明 |
| 3 | `intro`、`constructor`、`cases` | 掌握逻辑结构 |
| 4 | `rw`、`simp`、`calc` | 进行等式重写和化简 |
| 5 | `inductive`、递归、`induction` | 证明数据结构性质 |
| 6 | `List`、`Option`、`Except` | 结合真实程序建模 |
| 7 | mathlib、`ring`、`omega`、`linarith` | 使用成熟数学自动化 |
| 8 | 项目拆分、Lake、CI | 维护可复现的形式化项目 |

每次练习最好同时写出一个可计算函数和一个关于它的定理。例如先定义 `contains`，再证明空列表不包含任何元素；先定义排序函数，再证明结果长度不变。这样能一直保持“程序和规范相互配合”的感觉。

## 十四、Lean 和 AI 有什么关系？

Lean 不是大模型，但它非常适合作为大模型的验证后端。一个 AI coding agent 可以生成候选证明，Lean 负责检查候选证明是否真的符合类型；失败的错误信息又可以反馈给模型进行修复。

典型闭环是：

```text
自然语言目标
    -> LLM 生成 Lean 定理和证明
    -> Lean elaborator / tactic 执行
    -> kernel 检查证明项
    -> 成功：保存；失败：读取错误并修正
```

这里的关键边界是：LLM 可以负责搜索、翻译和提出证明草稿，但最终可信度来自 Lean 的检查器。对于数学研究、程序验证和 Agent 规划，这种“生成与验证分离”的架构比单纯要求模型输出一个看似合理的答案更可靠。

当然，形式化本身仍然需要人类决定定义、定理陈述和抽象边界。一个错误的 specification 可以被完美地证明，因此“证明通过”不等于“建模目标正确”。

## 十五、总结：先学会看目标，再学习自动化

Lean 4 的入门难点通常不是语法数量，而是需要改变思考方式：把“我想证明什么”明确写成类型，把证明过程看成逐步构造这个类型的值。

最值得先记住的几条经验是：

1. 用 `#check` 检查表达式和 lemma 的真实类型。
2. 用 proof state 理解当前上下文和目标，不要盲目堆 tactic。
3. 先掌握 `intro`、`exact`、`constructor`、`cases`、`rw`、`simp` 和 `induction`。
4. 把可计算程序、规范定理和测试例子放在同一个项目中。
5. 用 `lake build` 验证完整项目，而不只看编辑器局部提示。
6. 把 `sorry` 当作临时占位符，而不是最终证明。
7. 学会使用自动化，但也要理解自动化背后的目标形状。

Lean 最终带来的能力，是把程序的行为、数学的性质和机器检查的证据连接起来。对于刚接触形式化方法的人，最好的起点不是试图一次理解依赖类型理论的全部细节，而是每天写几个很小、但真正由 kernel 检查通过的定理。

## 参考资料

1. Lean 官方安装页：[Install Lean](https://lean-lang.org/install/)。
2. Lean 官方语言参考：[The Lean Language Reference](https://lean-lang.org/doc/reference/latest/)。
3. Jeremy Avigad、Leonardo de Moura、Soonho Kong、Sebastian Ullrich 等：[Theorem Proving in Lean 4](https://docs.lean-lang.org/theorem_proving_in_lean4/)。
4. Lean 官方 tactic 文档：[Tactic Proofs](https://lean-lang.org/doc/reference/latest/Tactic-Proofs/)。

