#!/bin/bash

# Criar estrutura de diretórios
mkdir -p aletheia/{downloaders,parsers,models,utils}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p examples
mkdir -p docs
mkdir -p .github/workflows

# Criar arquivos __init__.py
touch aletheia/__init__.py
touch aletheia/downloaders/__init__.py
touch aletheia/parsers/__init__.py
touch aletheia/models/__init__.py
touch aletheia/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

echo "✓ Estrutura criada"
