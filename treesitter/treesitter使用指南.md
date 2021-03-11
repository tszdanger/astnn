
# 
本文基于 https://tree-sitter.github.io/tree-sitter/using-parsers

由于原代码是C示例，慢慢改成python

## The Basic Objects

有4个Objects比较重要：languages, parsers, syntax trees, and syntax nodes.

    A TSLanguage is an opaque object that defines how to parse a particular programming language.
    这是别人写好的，不用动


    A TSParser is a stateful object that can be assigned a TSLanguage and used to produce a TSTree based on some source code.
    parser是一个带状态的object，给定source code 可以生成一个TSTree

    A TSTree represents the syntax tree of an entire source code file. It contains TSNode instances that indicate the structure of the source code. It can also be edited and used to produce a new TSTree in the event that the source code changes.
    TSTree 表示了源代码的syntax tree， 它包含了TSNode 实例，这些node可以被修改。（好像和python astvisitor那一套比较像）

    TSNode 是suntax tree的一个single node. 它track了开始和结束位置和 node与其他parent siblings children的关系。


一个C语言的example，解析json的
```c
// Filename - test-json-parser.c

#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <tree_sitter/api.h>

// Declare the `tree_sitter_json` function, which is
// implemented by the `tree-sitter-json` library.
TSLanguage *tree_sitter_json();

int main() {
  // Create a parser.
  TSParser *parser = ts_parser_new();

  // Set the parser's language (JSON in this case).
  ts_parser_set_language(parser, tree_sitter_json());

  // Build a syntax tree based on source code stored in a string.
  const char *source_code = "[1, null]";
  TSTree *tree = ts_parser_parse_string(
    parser,
    NULL,
    source_code,
    strlen(source_code)
  );

  // Get the root node of the syntax tree.
  TSNode root_node = ts_tree_root_node(tree);

  // Get some child nodes.
  // 节点+index访问？
  TSNode array_node = ts_node_named_child(root_node, 0);
  TSNode number_node = ts_node_named_child(array_node, 0);
    //有哪些内置类型呢？
  // Check that the nodes have the expected types.
  assert(strcmp(ts_node_type(root_node), "document") == 0);
  assert(strcmp(ts_node_type(array_node), "array") == 0);
  assert(strcmp(ts_node_type(number_node), "number") == 0);
    //children的数目
  // Check that the nodes have the expected child counts.
  assert(ts_node_child_count(root_node) == 1);
  assert(ts_node_child_count(array_node) == 5);
  assert(ts_node_named_child_count(array_node) == 2);
  assert(ts_node_child_count(number_node) == 0);
    //ts_node_string 打印？
  // Print the syntax tree as an S-expression.
  char *string = ts_node_string(root_node);
  printf("Syntax tree: %s\n", string);

  // Free all of the heap-allocated memory.
  free(string);
  ts_tree_delete(tree);
  ts_parser_delete(parser);
  return 0;
}


```


看看python的binding
```python
tree = parser.parse(bytes("""
def foo():
    if bar:
        baz()
""", "utf8"))
```

查看 `Tree`的结果:

```python
root_node = tree.root_node
assert root_node.type == 'module'
assert root_node.start_point == (1, 0)
assert root_node.end_point == (3, 13)

function_node = root_node.children[0]
assert function_node.type == 'function_definition'
assert function_node.child_by_field_name('name').type == 'identifier'

# 这里的问题是 如何找到type的定义 以及函数API文档在哪里找
# 看了一圈，难道是？ api.h ? 


function_name_node = function_node.children[1]
assert function_name_node.type == 'identifier'
assert function_name_node.start_point == (1, 4)
assert function_name_node.end_point == (1, 7)


# sexp() 是打印应该
assert root_node.sexp() == "(module "
    "(function_definition "
        "name: (identifier) "
        "parameters: (parameters) "
        "body: (block "
            "(if_statement "
                "condition: (identifier) "
                "consequence: (block "
                    "(expression_statement (call "
                        "function: (identifier) "
                        "arguments: (argument_list))))))))"

```


#### Walking Syntax Trees

If you need to traverse a large number of nodes efficiently, you can use
a `TreeCursor`:

```python
cursor = tree.walk()

assert cursor.node.type == 'module'

assert cursor.goto_first_child()
assert cursor.node.type == 'function_definition'

assert cursor.goto_first_child()
assert cursor.node.type == 'def'

# Returns `False` because the `def` node has no children

# 没有children返回 false
assert not cursor.goto_first_child()

assert cursor.goto_next_sibling()
assert cursor.node.type == 'identifier'

assert cursor.goto_next_sibling()
assert cursor.node.type == 'parameters'

assert cursor.goto_parent()
assert cursor.node.type == 'function_definition'
```

#### Editing

When a source file is edited, you can edit the syntax tree to keep it in sync with the source:

```python
tree.edit(
    start_byte=5,
    old_end_byte=5,
    new_end_byte=5 + 2,
    start_point=(0, 5),
    old_end_point=(0, 5),
    new_end_point=(0, 5 + 2),
)
```

Then, when you're ready to incorporate the changes into a new syntax tree,
you can call `Parser.parse` again, but pass in the old tree:

```python
new_tree = parser.parse(new_source, tree)

# 这里需要重新调用

```

This will run much faster than if you were parsing from scratch.

#### Pattern-matching

You can search for patterns in a syntax tree using a *tree query*:

```python
query = PY_LANGUAGE.query("""
(function_definition
  name: (identifier) @function.def)

(call
  function: (identifier) @function.call)
""")

captures = query.captures(tree.root_node)
assert len(captures) == 2
assert captures[0][0] == function_name_node
assert captures[0][1] == "function.def"
```



## Syntax Nodes


Tree-sitter provides a DOM-style interface for inspecting syntax trees. A syntax node’s type is a string that indicates which grammar rule the node represents.

node 的type访问出来就是string用来让人看的。
```
const char *ts_node_type(TSNode);
```

Syntax nodes 保存了原本的bytes序列号和 行列号 非常方便

```c
uint32_t ts_node_start_byte(TSNode);
uint32_t ts_node_end_byte(TSNode);

typedef struct {
  uint32_t row;
  uint32_t column;
} TSPoint;

TSPoint ts_node_start_point(TSNode);
TSPoint ts_node_end_point(TSNode);
```

通过rootnode可以访问其他节点

```c
TSNode ts_node_next_sibling(TSNode);
TSNode ts_node_prev_sibling(TSNode);
TSNode ts_node_parent(TSNode);

```

可能的返回值是 一个node，也可能是null

检查一下在pyhton里面返回的是什么。


### Named vs Anonymous Nodes

CST 和 AST 我们肯定是用AST 来进一步生成CFG之类的

 Tree-sitter’s trees support these use cases by making a distinction between named and anonymous nodes.


举个例子

```
if_statement: ($) => seq("if", "(", $._expression, ")", $._statement);

```
这里syntax node就会把if ( ) 这些都当成node
这些node不是named node
可以这样检查
```c
bool ts_node_is_named(TSNode);
```
When traversing the tree, you can also choose to skip over anonymous nodes by using the _named_ variants of all of the methods described above:

用下面这些方法就可以生成ast啦
```c
TSNode ts_node_named_child(TSNode, uint32_t);
uint32_t ts_node_named_child_count(TSNode);
TSNode ts_node_next_named_sibling(TSNode);
TSNode ts_node_prev_named_sibling(TSNode);
```

### Node Field Names
为了更容易分析，许多grammar会给特定的child nodes 分配unique的field,可以直接用field name来访问。

Fields also have numeric ids that you can use, if you want to avoid repeated string comparisons. You can convert between strings and ids using the TSLanguage:

fields name 和id 也是可以互相转换的

```c
uint32_t ts_language_field_count(const TSLanguage *);
const char *ts_language_field_name_for_id(const TSLanguage *, TSFieldId);
TSFieldId ts_language_field_id_for_name(const TSLanguage *, const char *, uint32_t);

```

fields id 和name api层面也提供了差不多的解析

```c
TSNode ts_node_child_by_field_id(TSNode, TSFieldId);
```


## Advanced Parsing
高级parsing
### editing 编辑
这一部分主要是editing的工作，和我们没啥关系
不过这种增量更新好像还可以


### Multi-language Documents
居然支持混合syntax tree
对于确定行 是别的语言的 tree，可以有单独的代码来分开解析

    This API allows for great flexibility in how languages can be composed. Tree-sitter is not responsible for mediating the interactions between languages. Instead, you are free to do that using arbitrary application-specific logic.

### Concurrency
支持多线程

    Internally, copying a syntax tree just entails incrementing an atomic reference count. Conceptually, it provides you a new tree which you can freely query, edit, reparse, or delete on a new thread while continuing to use the original tree on a different thread. Note that individual TSTree instances are not thread safe; you must copy a tree if you want to use it on multiple threads simultaneously.


## Other Tree Operations
### Walking Trees with Tree Cursors

为了更方便，我们选择用 cursor来完成。
初始化
```c
TSTreeCursor ts_tree_cursor_new(TSNode);
```
You can move the cursor around the tree:
```c
bool ts_tree_cursor_goto_first_child(TSTreeCursor *);
bool ts_tree_cursor_goto_next_sibling(TSTreeCursor *);
bool ts_tree_cursor_goto_parent(TSTreeCursor *);
```
These methods return true if the cursor successfully moved and false if there was no node to move to.

You can always retrieve the cursor’s current node, as well as the field name that is associated with the current node.
```c
TSNode ts_tree_cursor_current_node(const TSTreeCursor *);
const char *ts_tree_cursor_current_field_name(const TSTreeCursor *);
TSFieldId ts_tree_cursor_current_field_id(const TSTreeCursor *);
```


## Pattern Matching with Queries

Many code analysis tasks involve searching for patterns in syntax trees. Tree-sitter provides a small declarative language for expressing these patterns and searching for matches. The language is similar to the format of Tree-sitter’s unit test system.

很多代码分析中涉及到了在 语法树上做 模式匹配，我们提供了一种
dsl来进行这样的语法匹配。

 这种语言详见https://tree-sitter.github.io/tree-sitter/creating-parsers#the-grammar-dsl

### query

一个query = 许多pattern， 一个pattern 是一个代表很多syntax tree节点的S表达式

一个表达式由两部分组成
1. node的type
2. series of 该node的children（optional）

Children can also be omitted. For example, this would match any binary_expression where at least one of child is a string_literal node:

(binary_expression (string_literal))

### Fields

In general, it’s a good idea to make patterns more specific by specifying field names associated with child nodes. You do this by prefixing a child pattern with a field name followed by a colon. For example, this pattern would match an assignment_expression node where the left child is a member_expression whose object is a call_expression.
```
(assignment_expression
  left: (member_expression
    object: (call_expression)))
```

### Anonymous Nodes
The parenthesized syntax for writing nodes only applies to named nodes. To match specific anonymous nodes, you write their name between double quotes. For example, this pattern would match any binary_expression where the operator is != and the right side is null:
```
(binary_expression
  operator: "!="
  right: (null))
```
对于匿名nodes，必须用()再括一层


### Capturing Nodes

进行模式匹配时，可能需要根据名字来匹配
captures允许你把 names和特别的node 关联起来，用@符号
Capture names are written after the nodes that they refer to, and start with an @ character.

举例子

For example, this pattern would match any assignment of a function to an identifier, and it would associate the name the-function-name with the identifier:

(assignment_expression
  left: (identifier) @the-function-name
  right: (function))
And this pattern would match all method definitions, associating the name the-method-name with the method name, the-class-name with the containing class name:

(class_declaration
  name: (identifier) @the-class-name
  body: (class_body
    (method_definition
      name: (property_identifier) @the-method-name)))


### Quantification Operators

像正则一样写

You can match a repeating sequence of sibling nodes using the postfix + and * repetition operators, which work analogously to the + and * operators in regular expressions. The + operator matches one or more repetitions of a pattern, and the * operator matches zero or more.

For example, this pattern would match a sequence of one or more comments:
```
(comment)+
```
This pattern would match a class declaration, capturing all of the decorators if any were present:
```
(class_declaration
  (decorator)* @the-decorator
  name: (identifier) @the-name)
```
You can also mark a node as optional using the ? operator. For example, this pattern would match all function calls, capturing a string argument if one was present:
```
(call_expression
  function: (identifier) @the-function
  arguments: (arguments (string)? @the-string-arg))
```


### Grouping Sibling Nodes
You can also use parentheses for grouping a sequence of sibling nodes. For example, this pattern would match a comment followed by a function declaration:
```
(
  (comment)
  (function_declaration)
)
```
Any of the quantification operators mentioned above (+, *, and ?) can also be applied to groups. For example, this pattern would match a comma-separated series of numbers:
```
(
  (number)
  ("," (number))*
)
```

### Alternations
An alternation is written as a pair of square brackets ([]) containing a list of alternative patterns. This is similar to character classes from regular expressions ([abc] matches either a, b, or c).

For example, this pattern would match a call to either a variable or an object property. In the case of a variable, capture it as @function, and in the case of a property, capture it as @method:
```
(call_expression
  function: [
    (identifier) @function
    (member_expression
      property: (property_identifier) @method)
  ])
```
This pattern would match a set of possible keyword tokens, capturing them as @keyword:
```
[
  "break"
  "atch"
  "delete"
  "else"
  "for"
  "function"
  "if"
  "return"
  "try"
  "while"
] @keyword
```

### Wildcard Node
A wildcard node is represented with an underscore ((_)), it matches any node. This is similar to . in regular expressions.

For example, this pattern would match any node inside a call:

(call (_) @call.inner)
### Anchors
The anchor operator, ., is used to constrain the ways in which child patterns are matched. It has different behaviors depending on where it’s placed inside a query.

When . is placed before the first child within a parent pattern, the child will only match when it is the first named node in the parent. For example, the below pattern matches a given array node at most once, assigning the @the-element capture to the first identifier node in the parent array:

(array . (identifier) @the-element)
Without this anchor, the pattern would match once for every identifier in the array, with @the-element bound to each matched identifier.

Similarly, an anchor placed after a pattern’s last child will cause that child pattern to only match nodes that are the last named child of their parent. The below pattern matches only nodes that are the last named child within a block.

(block (_) @last-expression .)
Finally, an anchor between two child patterns will cause the patterns to only match nodes that are immediate siblings. The pattern below, given a long dotted name like a.b.c.d, will only match pairs of consecutive identifiers: a, b, b, c, and c, d.

(dotted_name
  (identifier) @prev-id
  .
  (identifier) @next-id)
Without the anchor, non-consecutive pairs like a, c and b, d would also be matched.

The restrictions placed on a pattern by an anchor operator ignore anonymous nodes.

### Predicates
You can also specify arbitrary metadata and conditions associed with a pattern by adding predicate S-expressions anywhere within your pattern. Predicate S-expressions start with a predicate name beginning with a # character. After that, they can contain an arbitrary number of @-prefixed capture names or strings.

For example, this pattern would match identifier whose names is written in SCREAMING_SNAKE_CASE:

(
  (identifier) @constant
  (#match? @constant "^[A-Z][A-Z_]+")
)
And this pattern would match key-value pairs where the value is an identifier with the same name as the key:

(
  (pair
    key: (property_identifier) @key-name
    value: (identifier) @value-name)
  (#eq? @key-name @value-name)
)
Note - Predicates are not handled directly by the Tree-sitter C library. They are just exposed in a structured form so that higher-level code can perform the filtering. However, higher-level bindings to Tree-sitter like the Rust crate or the WebAssembly binding implement a few common predicates like #eq? and #match?.


## Static Node Types


对于静态类型语言，提供了一个 node-types.json来做。

关于这部分的应用
    You can use this data to generate type declarations in statically-typed programming languages. For example, GitHub’s Semantic uses these node types files to generate Haskell data types for every possible syntax node, which allows for code analysis algorithms to be structurally verified by the Haskell type system.

### Basic Info
Every object in this array has these two entries:

"type" - A string that indicates which grammar rule the node represents. This corresponds to the ts_node_type function described above. 看属于哪一部分的语法规则

"named" - A boolean that indicates whether this kind of node corresponds to a rule name in the grammar or just a string literal. See above for more info. 布尔型，是规则名或者只是简单的string

Examples:
```
{
  "type": "string_literal",
  "named": true
}
{
  "type": "+",
  "named": false
}
```
Together, these two fields constitute a unique identifier for a node type; no two top-level objects in the node-types.json should have the same values for both "type" and "named".

### Internal Nodes
Many syntax nodes can have children. The node type object describes the possible children that a node can have using the following entries:

一个nodetype对象可能会有以下两点：

"fields" - An object that describes the possible fields that the node can have. The keys of this object are field names, and the values are child type objects, described below.

其中key是 field names, values是child type

"children" - Another child type object that describes all of the node’s possible named children without fields.

A child type object describes a set of child nodes using the following entries:

一个child对象 会用以下三个key来描述一些node。

"required" - A boolean indicating whether there is always at least one node in this set.

"multiple" - A boolean indicating whether there can be multiple nodes in this set.

"types"- An array of objects that represent the possible types of nodes in this set. Each object has two keys: "type" and "named", whose meanings are described above.
Example with fields:

### Supertype Nodes

In Tree-sitter grammars, there are usually certain rules that represent abstract categories of syntax nodes (e.g. “expression”, “type”, “declaration”). In the grammar.js file, these are often written as hidden rules whose definition is a simple choice where each member is just a single symbol.

Normally, hidden rules are not mentioned in the node types file, since they don’t appear in the syntax tree. But if you add a hidden rule to the grammar’s supertypes list, then it will show up in the node types file, with the following special entry:

"subtypes" - An array of objects that specify the types of nodes that this ‘supertype’ node can wrap.
Example:
```
{
  "type": "_declaration",
  "named": true,
  "subtypes": [
    { "type": "class_declaration", "named": true },
    { "type": "function_declaration", "named": true },
    { "type": "generator_function_declaration", "named": true },
    { "type": "lexical_declaration", "named": true },
    { "type": "variable_declaration", "named": true }
  ]
}
```
Supertype nodes will also appear elsewhere in the node types file, as children of other node types, in a way that corresponds with how the supertype rule was used in the grammar. This can make the node types much shorter and easier to read, because a single supertype will take the place of multiple subtypes.

Example:
```
{
  "type": "export_statement",
  "named": true,
  "fields": {
    "declaration": {
      "multiple": false,
      "required": false,
      "types": [{ "type": "_declaration", "named": true }]
    },
    "source": {
      "multiple": false,
      "required": false,
      "types": [{ "type": "string", "named": true }]
    }
  }
}

```

