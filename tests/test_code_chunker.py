from pocketpaw.search.chunkers.code import CodeChunker


def test_python_function_split():
    code = """import os

def hello():
    print("hello")

def world():
    print("world")

class Foo:
    def bar(self):
        pass
"""
    chunker = CodeChunker()
    chunks = chunker.chunk(code, file_path="/app.py")
    assert len(chunks) >= 3  # hello, world, Foo
    names = [c.metadata.get("symbol") for c in chunks]
    assert "hello" in names
    assert "world" in names
    assert "Foo" in names


def test_javascript_split():
    code = """function greet(name) {
  return "Hi " + name;
}

const add = (a, b) => {
  return a + b;
};

class Calculator {
  multiply(a, b) {
    return a * b;
  }
}
"""
    chunker = CodeChunker()
    chunks = chunker.chunk(code, file_path="/app.js")
    assert len(chunks) >= 2


def test_empty_file():
    chunker = CodeChunker()
    assert chunker.chunk("", file_path="/empty.py") == []


def test_unknown_extension_falls_back():
    chunker = CodeChunker()
    chunks = chunker.chunk("some content here", file_path="/file.xyz")
    assert len(chunks) == 1
