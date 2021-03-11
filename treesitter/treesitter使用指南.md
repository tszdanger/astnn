
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
对于确定行 是别的语言的 tree，


