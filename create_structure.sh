#!/bin/bash

# Criar estrutura de diretórios
mkdir -p b3quant/{downloaders,parsers,models,utils}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p examples
mkdir -p docs
mkdir -p .github/workflows

# Criar arquivos __init__.py
touch b3quant/__init__.py
touch b3quant/downloaders/__init__.py
touch b3quant/parsers/__init__.py
touch b3quant/models/__init__.py
touch b3quant/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

echo "✓ Estrutura criada"
