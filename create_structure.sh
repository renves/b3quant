#!/bin/bash

# Criar estrutura de diretórios
mkdir -p pybovespa/{downloaders,parsers,models,utils}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p examples
mkdir -p docs
mkdir -p .github/workflows

# Criar arquivos __init__.py
touch pybovespa/__init__.py
touch pybovespa/downloaders/__init__.py
touch pybovespa/parsers/__init__.py
touch pybovespa/models/__init__.py
touch pybovespa/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

echo "✓ Estrutura criada"
