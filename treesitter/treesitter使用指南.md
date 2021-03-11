
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
```
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





