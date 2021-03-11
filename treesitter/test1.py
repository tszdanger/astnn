from tree_sitter import Language, Parser

Language.build_library(
  # Store the library in the `build` directory
  './my-languages.so',

  # Include one or more languages
  [
    'tree-sitter-cpp',
    'tree-sitter-c'
  ]
)

CPP_LANGUAGE = Language('./my-languages.so', 'cpp')
PY_LANGUAGE = Language('./my-languages.so', 'c')

parser = Parser()
parser.set_language(PY_LANGUAGE)

tree = parser.parse(bytes("""
int main():{
  int a = 1;
  return a;
}
""", "utf8"))


# root_node = tree.root_node
# print(root_node.sexp())

print(1)
