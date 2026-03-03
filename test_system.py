#!/usr/bin/env python3
"""
Script de Teste e Validação do Sistema de Solicitação de Punição

Este script realiza testes básicos das funcionalidades do sistema
para garantir que tudo esteja funcionando corretamente.
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório atual ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig, validate_config


def test_config_validation():
    """Testa a validação das configurações."""
    print("🔍 Testando validação de configurações...")
    
    errors = validate_config()
    
    if errors:
        print("❌ Erros encontrados:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("✅ Configurações válidas!")
        return True


def test_punishment_system_config():
    """Testa as configurações do sistema de punição."""
    print("\n🔧 Testando configurações do sistema de punição...")
    
    config = BotConfig.PunishmentSystem
    
    # Testa valores mínimos e máximos
    assert config.TIMEOUT_MINUTES > 0, "TIMEOUT_MINUTES deve ser maior que 0"
    assert config.MAX_QUANTITY > 0, "MAX_QUANTITY deve ser maior que 0"
    assert config.MIN_QUANTITY > 0, "MIN_QUANTITY deve ser maior que 0"
    assert config.MIN_MOTIVO_LENGTH > 0, "MIN_MOTIVO_LENGTH deve ser maior que 0"
    
    # Testa consistência entre min e max
    assert config.MIN_QUANTITY <= config.MAX_QUANTITY, "MIN_QUANTITY deve ser menor ou igual a MAX_QUANTITY"
    
    # Testa tipos de imagens
    assert len(config.VALID_IMAGE_TYPES) > 0, "Deve haver tipos de imagens válidos"
    assert len(config.VALID_IMAGE_EXTENSIONS) > 0, "Deve haver extensões de imagens válidas"
    
    print("✅ Configurações do sistema de punição válidas!")
    return True


def test_image_validation():
    """Testa a validação de imagens (simulação)."""
    print("\n📸 Testando validação de imagens...")
    
    config = BotConfig.PunishmentSystem
    
    # Testa extensões válidas
    valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff']
    for ext in valid_extensions:
        assert ext in config.VALID_IMAGE_EXTENSIONS, f"Extensão {ext} deve ser válida"
    
    # Testa tipos MIME válidos
    valid_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
                   'image/webp', 'image/bmp', 'image/tiff']
    for mime_type in valid_types:
        assert mime_type in config.VALID_IMAGE_TYPES, f"Tipo MIME {mime_type} deve ser válido"
    
    print("✅ Validação de imagens configurada corretamente!")
    return True


def test_logging_config():
    """Testa a configuração de logging."""
    print("\n📝 Testando configuração de logging...")
    
    config = BotConfig.Logging
    
    # Testa nível de log válido
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    assert config.LOG_LEVEL in valid_levels, f"Nível de log inválido: {config.LOG_LEVEL}"
    
    # Testa formato de log
    assert len(config.LOG_FORMAT) > 0, "Formato de log não pode ser vazio"
    
    print("✅ Configuração de logging válida!")
    return True


def test_guild_config():
    """Testa a configuração de guilds."""
    print("\n📡 Testando configuração de guilds...")
    
    # Testa se há guilds configuradas (pode ser vazio para produção)
    assert isinstance(BotConfig.TEST_GUILDS, list), "TEST_GUILDS deve ser uma lista"
    
    # Se houver guilds, verifica se são IDs válidos
    for guild_id in BotConfig.TEST_GUILDS:
        assert isinstance(guild_id, int), f"ID de guild inválido: {guild_id}"
        assert guild_id > 0, f"ID de guild deve ser positivo: {guild_id}"
    
    print("✅ Configuração de guilds válida!")
    return True


def print_system_info():
    """Imprime informações sobre o sistema."""
    print("\n📊 Informações do Sistema")
    print("=" * 50)
    
    print(f"⏰ Timeout: {BotConfig.PunishmentSystem.TIMEOUT_MINUTES} minutos")
    print(f"🔢 Quantidade Máxima: {BotConfig.PunishmentSystem.MAX_QUANTITY} JJ's")
    print(f"🔢 Quantidade Mínima: {BotConfig.PunishmentSystem.MIN_QUANTITY} JJ's")
    print(f"📝 Tamanho Mínimo do Motivo: {BotConfig.PunishmentSystem.MIN_MOTIVO_LENGTH} caracteres")
    print(f"📸 Tipos de Imagem: {len(BotConfig.PunishmentSystem.VALID_IMAGE_TYPES)} suportados")
    print(f"📡 Guilds de Teste: {len(BotConfig.TEST_GUILDS)} configuradas")
    print(f"📝 Nível de Log: {BotConfig.Logging.LOG_LEVEL}")
    
    if BotConfig.Logging.LOG_FILE:
        print(f"📁 Arquivo de Log: {BotConfig.Logging.LOG_FILE}")
    else:
        print("📁 Arquivo de Log: Console (padrão)")
    
    print(f"⏰ Teste realizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Função principal de teste."""
    print("🧪 Iniciando Testes do Sistema de Solicitação de Punição")
    print("=" * 60)
    
    tests = [
        test_config_validation,
        test_punishment_system_config,
        test_image_validation,
        test_logging_config,
        test_guild_config
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test in tests:
        try:
            if test():
                passed_tests += 1
        except Exception as e:
            print(f"❌ Erro no teste {test.__name__}: {e}")
    
    print_system_info()
    
    print("\n" + "=" * 60)
    print(f"🎯 Resultado dos Testes: {passed_tests}/{total_tests} aprovados")
    
    if passed_tests == total_tests:
        print("✅ Todos os testes foram aprovados! O sistema está pronto para uso.")
        return 0
    else:
        print("❌ Alguns testes falharam. Por favor, corrija os problemas antes de usar o bot.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)