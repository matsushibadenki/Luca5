# all_python_tools/enhanced_python_analyzer.py
# title: Enhanced Python Project Structure Aggregator
# role: Aggregates Python project structure with additional analysis for AI comprehension

import os
import ast
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Optional, Union, Tuple, Any, cast

def get_project_tree(start_path: Union[str, Path], ignore_dirs: Set[str], indent: str = '') -> str:
    """
    Generates a tree-like string representation of the project structure.
    プロジェクト構造のツリー状の文字列表現を生成します。
    """
    tree_str = ''
    try:
        items = sorted(list(Path(start_path).iterdir()))
    except FileNotFoundError:
        return ""
    valid_items = [item for item in items if item.name not in ignore_dirs]
    
    for i, item in enumerate(valid_items):
        is_last = (i == len(valid_items) - 1)
        tree_str += indent
        if is_last:
            tree_str += '└── '
            next_indent = indent + '    '
        else:
            tree_str += '├── '
            next_indent = indent + '│   '
            
        if item.is_file() and item.suffix == '.py':
            try:
                size = item.stat().st_size
                tree_str += f"{item.name} ({size} bytes)\n"
            except FileNotFoundError:
                tree_str += f"{item.name} (file not found)\n"
        else:
            tree_str += item.name + '\n'
            
        if item.is_dir():
            tree_str += get_project_tree(item, ignore_dirs, next_indent)
    return tree_str

class CustomASTVisitor(ast.NodeVisitor):
    """
    A custom AST visitor to collect detailed information from Python code.
    Pythonコードから詳細な情報を収集するためのカスタムASTビジターです。
    """
    def __init__(self):
        self.imports: List[str] = []
        self.from_imports: List[str] = []
        self.functions: List[str] = []
        self.classes: List[str] = []
        self.constants: List[str] = []
        self.di_container_instantiations: List[str] = []
        self.di_registrations: List[str] = []
        self.injected_dependencies: List[str] = []
        self.langchain_components: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ''
        for alias in node.names:
            self.from_imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        # Check for constructor injection patterns
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == '__init__':
                for arg in item.args.args:
                    if arg.arg != 'self':
                        self.injected_dependencies.append(f"{node.name}.__init__({arg.arg})")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                self.constants.append(target.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Detect DI Container instantiations (e.g., Container(), Dependant())
        if isinstance(node.func, ast.Name) and node.func.id in ['Container', 'Provider', 'Dependant', 'Injector']:
            self.di_container_instantiations.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Detect DI Container registrations (e.g., container.register(), builder.build())
            if node.func.attr in ['register', 'bind', 'provide', 'factory', 'singleton', 'instance', 'build']:
                if isinstance(node.func.value, ast.Name):
                    self.di_registrations.append(f"{node.func.value.id}.{node.func.attr}")
                elif isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == 'Container':
                    self.di_registrations.append(f"Container().{node.func.attr}")
            
            # Detect LangChain component instantiations (common classes)
            langchain_components = [
                'ChatOpenAI', 'OpenAI', 'HuggingFaceHub', 'LlamaCpp', # LLMs
                'PromptTemplate', 'ChatPromptTemplate', # Prompts
                'LLMChain', 'SimpleSequentialChain', 'ConversationalRetrievalChain', # Chains
                'AgentExecutor', 'initialize_agent', # Agents
                'Tool', 'create_tool_calling_agent', # Tools
                'VectorStoreRetriever', 'Chroma', 'FAISS', # Retrievers/Vector Stores
                'RunnableSequence', 'RunnableParallel' # LCEL
            ]
            if node.func.attr in langchain_components:
                if isinstance(node.func.value, ast.Name):
                    # e.g., from langchain.llms import OpenAI; llm = OpenAI()
                    self.langchain_components.append(node.func.attr)
                elif isinstance(node.func.value, ast.Attribute) and node.func.value.attr in ['llms', 'chains', 'agents', 'tools', 'prompts', 'retrievers', 'vectorstores', 'runnables']:
                    # e.g., llm = langchain.llms.OpenAI()
                    self.langchain_components.append(node.func.attr)
        self.generic_visit(node)

    def visit_Decorator(self, node: ast.expr) -> None:
        # Detect @inject decorator (e.g., dependency-injector)
        if isinstance(node, ast.Name) and node.id == 'inject':
            # This decorator usually applies to functions or methods
            # Note: ast.NodeVisitor does not have a 'parent' attribute by default.
            # This part would require a custom AST walker that tracks parents,
            # or a different approach if direct parent access is needed.
            # For simplicity, we'll just note the decorator's presence.
            pass # We handle decorators on FunctionDef/ClassDef directly by checking node.decorator_list
        self.generic_visit(node)

def extract_module_details(file_path: Path) -> Dict[str, Any]:
    """
    Extract imports, function definitions, class definitions, constants,
    DI container related patterns, and LangChain component usage from a Python file.
    Pythonファイルからインポート、関数定義、クラス定義、定数、
    DIコンテナ関連パターン、LangChainコンポーネントの使用状況を抽出します。
    """
    result: Dict[str, Any] = {
        'imports': [],
        'from_imports': [],
        'functions': [],
        'classes': [],
        'constants': [],
        'di_container_instantiations': [],
        'di_registrations': [],
        'injected_dependencies': [],
        'langchain_components': [],
        'parse_error': None
    }
    
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        visitor = CustomASTVisitor()
        visitor.visit(tree)

        result['imports'] = visitor.imports
        result['from_imports'] = visitor.from_imports
        result['functions'] = visitor.functions
        result['classes'] = visitor.classes
        result['constants'] = visitor.constants
        result['di_container_instantiations'] = visitor.di_container_instantiations
        result['di_registrations'] = visitor.di_registrations
        result['injected_dependencies'] = visitor.injected_dependencies
        result['langchain_components'] = visitor.langchain_components

        # Additional check for @inject decorators on functions/classes
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'inject':
                        result['injected_dependencies'].append(f"@{decorator.id} applied to {node.name}")
                    elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == 'inject':
                        result['injected_dependencies'].append(f"@{decorator.func.id} applied to {node.name}")

    except Exception as e:
        result['parse_error'] = str(e)
    
    return result

def analyze_module_dependencies(project_path: Path, ignore_dirs: Set[str]) -> Dict[str, List[str]]:
    """
    Analyze dependencies between modules within the project.
    プロジェクト内のモジュール間の依存関係を分析します。
    """
    dependencies: Dict[str, List[str]] = defaultdict(list)
    all_modules: Set[str] = set()
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_path)
                module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
                all_modules.add(module_name)
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_path)
                current_module = str(relative_path.with_suffix('')).replace(os.sep, '.')
                
                analysis = extract_module_details(file_path)
                imports_to_check: List[str] = (analysis['imports'] if 'imports' in analysis else []) + \
                                             (analysis['from_imports'] if 'from_imports' in analysis else [])
                
                for imp in imports_to_check:
                    if isinstance(imp, str):
                        for module in all_modules:
                            # Check if the import starts with a project module or is a sub-module
                            # インポートがプロジェクトモジュールで始まるか、サブモジュールであるかを確認します。
                            if imp == module or imp.startswith(f"{module}.") or module.startswith(f"{imp}."):
                                dependencies[current_module].append(imp)
                                break
    
    return dependencies

def get_project_summary(project_path: Path, ignore_dirs: Set[str]) -> Dict[str, Any]:
    """
    Generate a high-level summary of the project.
    プロジェクトの概要を生成します。
    """
    summary: Dict[str, Any] = {
        'total_py_files': 0,
        'total_lines': 0,
        'main_modules': [],
        'test_files': [],
        'config_files': [],
        'largest_files': [],
        'module_test_associations': defaultdict(list)
    }
    
    file_sizes: List[Tuple[str, int]] = []
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            file_path = Path(root) / file
            
            if not file_path.exists():
                continue

            relative_path = file_path.relative_to(project_path)
            
            if file.endswith('.py'):
                summary['total_py_files'] += 1
                size = file_path.stat().st_size
                file_sizes.append((str(relative_path), size))
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                        summary['total_lines'] += lines
                except Exception:
                    pass
                
                if 'test' in file.lower() or 'test' in str(relative_path).lower():
                    summary['test_files'].append(str(relative_path))
                    # Attempt to associate test file with a module
                    # テストファイルをモジュールに関連付けようと試みます。
                    # Basic heuristic: if test_module.py exists, look for module.py or module/
                    # 基本的なヒューリスティック: test_module.py が存在する場合、module.py または module/ を探します。
                    module_name_guess = file.lower().replace('test_', '').replace('_test', '').replace('.py', '')
                    if module_name_guess and module_name_guess != file.lower().replace('.py', ''):
                        potential_module_path = file_path.parent / f"{module_name_guess}.py"
                        if potential_module_path.exists():
                            summary['module_test_associations'][str(potential_module_path.relative_to(project_path))].append(str(relative_path))
                        else:
                            # Check for module in parent directory (e.g., tests/module/test_module.py)
                            # 親ディレクトリ内のモジュールを確認します (例: tests/module/test_module.py)。
                            potential_module_dir = file_path.parent / module_name_guess
                            if potential_module_dir.is_dir():
                                summary['module_test_associations'][str(potential_module_dir.relative_to(project_path))].append(str(relative_path))

                elif file in ['main.py', 'app.py', '__main__.py', 'run.py']:
                    summary['main_modules'].append(str(relative_path))
            elif file.endswith(('.ini', '.cfg', '.conf', '.yaml', '.yml', '.json', '.toml', '.env')): # Added .env
                summary['config_files'].append(str(relative_path))
    
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    summary['largest_files'] = file_sizes[:5]
    
    return summary

def aggregate_enhanced_project_structure(project_path: str, output_file: str, ignore_dirs: Optional[Set[str]] = None, ignore_files: Optional[Set[str]] = None, include_analysis: bool = True):
    """
    Enhanced aggregation with dependency analysis and project summary.
    依存関係分析とプロジェクト概要を含む強化された集約。
    """
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', 'venv', '.venv', 'node_modules', 'dist', 'build', '.pytest_cache'}
    if ignore_files is None:
        ignore_files = {'.DS_Store'}

    project_path_obj = Path(project_path)
    output_path = Path(output_file)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Project Analysis: {project_path_obj.name}\n\n")
        
        if include_analysis:
            summary = get_project_summary(project_path_obj, ignore_dirs)
            f.write("## Project Summary\n\n")
            f.write(f"- **Total Python files**: {summary['total_py_files']}\n")
            f.write(f"- **Total lines of code**: {summary['total_lines']:,}\n")
            f.write(f"- **Main modules**: {', '.join(summary['main_modules']) if summary['main_modules'] else 'None detected'}\n")
            f.write(f"- **Test files**: {len(summary['test_files'])}\n")
            f.write(f"- **Config files**: {len(summary['config_files'])}\n\n")
            
            if summary['largest_files']:
                f.write("### Largest Files\n")
                for file_p, size in summary['largest_files']:
                    f.write(f"- `{file_p}`: {size:,} bytes\n")
                f.write("\n")

            if summary['module_test_associations']:
                f.write("### Module to Test File Associations\n")
                for module, tests in summary['module_test_associations'].items():
                    f.write(f"- `{module}` is tested by: {', '.join(tests)}\n")
                f.write("\n")


        f.write("## 1. Project Directory Structure\n\n")
        f.write("```\n")
        tree_view = get_project_tree(project_path_obj, ignore_dirs)
        f.write(f"{project_path_obj.name}\n{tree_view}")
        f.write("```\n\n")
        
        f.write("## 2. Dependencies\n\n")
        dependency_files = ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile', 'environment.yml']
        found_deps = False
        for dep_file in dependency_files:
            dep_path = project_path_obj / dep_file
            if dep_path.is_file():
                found_deps = True
                f.write(f"### `{dep_file}`\n\n")
                f.write("```\n")
                f.write(dep_path.read_text(encoding='utf-8'))
                f.write("\n```\n\n")
        if not found_deps:
            f.write("No dependency files found.\n\n")

        if include_analysis:
            f.write("## 3. Internal Module Dependencies\n\n")
            dependencies = analyze_module_dependencies(project_path_obj, ignore_dirs)
            if dependencies:
                for module, deps in sorted(dependencies.items()):
                    if deps:
                        f.write(f"### `{module}`\n")
                        f.write("Dependencies:\n")
                        for dep in sorted(list(set(deps))):
                            f.write(f"- {dep}\n")
                        f.write("\n")
            else:
                f.write("No internal dependencies detected.\n\n")
            
            # --- New Sections for DI/LangChain Analysis ---
            f.write("## 4. DI Container and LangChain Analysis Overview\n\n")
            py_files = sorted(project_path_obj.rglob('*.py'))
            
            di_analysis_found = False
            langchain_analysis_found = False

            for file_path in py_files:
                if not any(part in ignore_dirs for part in file_path.parts):
                    relative_path = file_path.relative_to(project_path_obj)
                    analysis = extract_module_details(file_path)
                    
                    if analysis['parse_error']:
                        f.write(f"### `{relative_path}`\n")
                        f.write(f"⚠️ Parse error: {analysis['parse_error']}\n\n")
                        continue
                    
                    if analysis['di_container_instantiations'] or \
                       analysis['di_registrations'] or \
                       analysis['injected_dependencies']:
                        di_analysis_found = True
                        f.write(f"### `{relative_path}` (DI Container Analysis)\n")
                        if analysis['di_container_instantiations']:
                            f.write(f"**DI Container Instantiations**: {', '.join(analysis['di_container_instantiations'])}\n")
                        if analysis['di_registrations']:
                            f.write(f"**DI Registrations/Bindings**: {', '.join(analysis['di_registrations'])}\n")
                        if analysis['injected_dependencies']:
                            f.write(f"**Injected Dependencies**: {', '.join(analysis['injected_dependencies'])}\n")
                        f.write("\n")
                    
                    if analysis['langchain_components']:
                        langchain_analysis_found = True
                        f.write(f"### `{relative_path}` (LangChain Analysis)\n")
                        f.write(f"**LangChain Components Used**: {', '.join(sorted(list(set(analysis['langchain_components']))))}\n")
                        f.write("\n")
            
            if not di_analysis_found:
                f.write("No explicit DI Container patterns detected.\n\n")
            if not langchain_analysis_found:
                f.write("No explicit LangChain components detected.\n\n")

            f.write("## 5. File Analysis Overview\n\n") # Renumbered from 4 to 5
            py_files = sorted(project_path_obj.rglob('*.py'))
            for file_path in py_files:
                if not any(part in ignore_dirs for part in file_path.parts):
                    relative_path = file_path.relative_to(project_path_obj)
                    analysis = extract_module_details(file_path) # Changed to extract_module_details
                    
                    f.write(f"### `{relative_path}`\n")
                    if analysis['parse_error']:
                        f.write(f"⚠️ Parse error: {analysis['parse_error']}\n\n")
                        continue
                        
                    if analysis['classes']:
                        f.write(f"**Classes**: {', '.join(analysis['classes'])}\n")
                    if analysis['functions']:
                        f.write(f"**Functions**: {', '.join(analysis['functions'])}\n")
                    all_imports: List[str] = (analysis['imports'] if 'imports' in analysis else []) + \
                                             (analysis['from_imports'] if 'from_imports' in analysis else [])
                    external_imports = [imp for imp in all_imports if isinstance(imp, str) and not imp.startswith('.')]
                    if external_imports:
                        f.write(f"**External imports**: {', '.join(sorted(list(set(external_imports))))}\n")
                    if analysis['constants']:
                        f.write(f"**Constants**: {', '.join(analysis['constants'])}\n")
                    f.write("\n")
            # --- End of New Sections ---

        f.write("## 6. Source Code\n\n") # Renumbered from 5 to 6
        py_files = sorted(project_path_obj.rglob('*.py'))
        for file_path in py_files:
            if not any(part in ignore_dirs for part in file_path.parts) and file_path.name not in (ignore_files or set()):
                relative_path = file_path.relative_to(project_path_obj)
                
                f.write(f"### `{relative_path}`\n\n")
                f.write("```python\n")
                try:
                    content = file_path.read_text(encoding='utf-8')
                    f.write(content)
                except Exception as e:
                    f.write(f"# Error reading file: {e}")
                f.write("\n```\n\n")

    print(f"✅ Enhanced project structure aggregated into: {output_file}")


if __name__ == '__main__':
    PROJECT_DIRECTORY = '.'
    OUTPUT_MARKDOWN_FILE = 'enhanced_project_structure.md'
    INCLUDE_ANALYSIS = True

    aggregate_enhanced_project_structure(
        PROJECT_DIRECTORY, 
        OUTPUT_MARKDOWN_FILE,
        include_analysis=INCLUDE_ANALYSIS
    )
