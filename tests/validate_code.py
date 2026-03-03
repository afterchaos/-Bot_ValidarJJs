#!/usr/bin/env python3
"""
Script de Validação de Código

Este script valida a sintaxe dos arquivos Python e verifica
se as importações básicas estão corretas.
"""

import ast
import sys
import os


def validate_python_syntax(file_path):
    """Valida a sintaxe de um arquivo Python."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Tenta fazer o parsing da AST
        ast.parse(source)
        return True, "Sintaxe válida"
    
    except SyntaxError as e:
        return False, f"Erro de sintaxe: {e}"
    except Exception as e:
        return False, f"Erro ao ler arquivo: {e}"


def check_imports(file_path):
    """Verifica as importações básicas no arquivo."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        
        return True, imports
    
    except Exception as e:
        return False, f"Erro ao analisar imports: {e}"


def main():
    """Função principal de validação."""
    print("Validando Código do Sistema de Punição")
    print("=" * 50)
    
    files_to_check = [
        'main.py',
        'config.py',
        'test_system.py'
    ]
    
    all_valid = True
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"❌ Arquivo não encontrado: {file_path}")
            all_valid = False
            continue
        
        print(f"\nValidando: {file_path}")
        
        # Valida sintaxe
        syntax_valid, syntax_msg = validate_python_syntax(file_path)
        if syntax_valid:
            print(f"  Sintaxe: {syntax_msg}")
        else:
            print(f"  Sintaxe: {syntax_msg}")
            all_valid = False
        
        # Verifica imports
        imports_valid, imports = check_imports(file_path)
        if imports_valid:
            print(f"  Imports: {len(imports)} encontrados")
            if file_path == 'main.py':
                required_imports = ['disnake', 'commands', 'Embed', 'Color']
                missing = [imp for imp in required_imports if any(req in str(imp) for req in required_imports)]
                if missing:
                    print(f"  Imports críticos: {missing}")
        else:
            print(f"  Imports: {imports}")
            all_valid = False
    
    print("\n" + "=" * 50)
    if all_valid:
        print("Validação concluída com sucesso!")
        print("O código está pronto para ser executado (após instalar o Python e as dependências).")
    else:
        print("Erros encontrados na validação.")
        print("Por favor, corrija os problemas antes de executar o bot.")
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)