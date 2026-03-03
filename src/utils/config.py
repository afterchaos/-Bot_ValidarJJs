#!/usr/bin/env python3
"""
Configurações do Sistema de Solicitação de Punição

Este arquivo contém todas as configurações do bot para fácil personalização.
"""

import os
from typing import List
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()


class BotConfig:
    """Configurações principais do bot."""
    
    # Token do bot (obrigatório) - Carregado do .env
    BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
    
    # IDs dos servidores de teste (para comandos slash) - Carregado do .env
    TEST_GUILD_IDS_STR = os.getenv("TEST_GUILD_IDS", "")
    TEST_GUILDS: List[int] = []
    
    # Converte a string de IDs para lista de inteiros
    if TEST_GUILD_IDS_STR:
        try:
            TEST_GUILDS = [int(guild_id.strip()) for guild_id in TEST_GUILD_IDS_STR.split(',') if guild_id.strip()]
        except ValueError:
            print("⚠️  Aviso: TEST_GUILD_IDS contém valores inválidos. Use IDs numéricos separados por vírgula.")
            TEST_GUILDS = []
    
    # Configurações do sistema de punição
    class PunishmentSystem:
        """Configurações do sistema de punição."""
        
        # Tempo limite para envio da foto (em minutos) - Carregado do .env
        TIMEOUT_MINUTES = int(os.getenv("TIMEOUT_MINUTES", "5"))
        
        # Quantidade máxima de JJ's permitida - Carregado do .env
        MAX_QUANTITY = int(os.getenv("MAX_QUANTITY", "10000"))
        
        # Quantidade mínima de JJ's - Carregado do .env
        MIN_QUANTITY = int(os.getenv("MIN_QUANTITY", "1"))
        
        # Tamanho mínimo do motivo (em caracteres) - Carregado do .env
        MIN_MOTIVO_LENGTH = int(os.getenv("MIN_MOTIVO_LENGTH", "5"))
        
        # IDs dos cargos responsáveis pela análise (ex: Moderador/Superior)
        # Suporta múltiplos cargos separados por vírgula
        RESPONSIBLE_ROLE_IDS_STR = os.getenv("RESPONSIBLE_ROLE_IDS", "")
        RESPONSIBLE_ROLE_IDS: List[int] = []
        
        # Converte a string de IDs para lista de inteiros
        if RESPONSIBLE_ROLE_IDS_STR:
            try:
                RESPONSIBLE_ROLE_IDS = [int(role_id.strip()) for role_id in RESPONSIBLE_ROLE_IDS_STR.split(',') if role_id.strip()]
            except ValueError:
                print("⚠️  Aviso: RESPONSIBLE_ROLE_IDS contém valores inválidos. Use IDs numéricos separados por vírgula.")
                RESPONSIBLE_ROLE_IDS = []
        
        # Para compatibilidade com código existente, mantém RESPONSIBLE_ROLE_ID como o primeiro da lista
        RESPONSIBLE_ROLE_ID = RESPONSIBLE_ROLE_IDS[0] if RESPONSIBLE_ROLE_IDS else 0
        
        # ID do canal público de punições (onde serão enviados os relatórios de punição)
        PUNISHMENTS_CHANNEL_ID = int(os.getenv("PUNISHMENTS_CHANNEL_ID", "0"))
        
        # ID da categoria onde os canais de punição serão criados
        PUNISHMENT_CATEGORY_ID = int(os.getenv("PUNISHMENT_CATEGORY_ID", "0"))
        
        # ID do canal de solicitações (onde os militares solicitam punições)
        REQUESTS_CHANNEL_ID = int(os.getenv("REQUESTS_CHANNEL_ID", "0"))
        
        # ID do canal de aprovação (onde os cargos responsáveis analisam e aprovam/reprovam)
        APPROVAL_CHANNEL_ID = int(os.getenv("APPROVAL_CHANNEL_ID", "0"))
        
        # IDs dos cargos permitidos para usar os comandos de punição (separados por vírgula)
        ALLOWED_ROLES_IDS_STR = os.getenv("ALLOWED_ROLES_IDS", "")
        ALLOWED_ROLES_IDS: List[int] = []
        
        # Converte a string de IDs para lista de inteiros
        if ALLOWED_ROLES_IDS_STR:
            try:
                ALLOWED_ROLES_IDS = [int(role_id.strip()) for role_id in ALLOWED_ROLES_IDS_STR.split(',') if role_id.strip()]
            except ValueError:
                print("⚠️  Aviso: ALLOWED_ROLES_IDS contém valores inválidos. Use IDs numéricos separados por vírgula.")
                ALLOWED_ROLES_IDS = []
        
        # IDs dos cargos permitidos para usar o comando /limpar-punicoes (separados por vírgula)
        CLEAR_PUNISHMENTS_ROLE_IDS_STR = os.getenv("CLEAR_PUNISHMENTS_ROLE_IDS", "")
        CLEAR_PUNISHMENTS_ROLE_IDS: List[int] = []
        
        # Converte a string de IDs para lista de inteiros
        if CLEAR_PUNISHMENTS_ROLE_IDS_STR:
            try:
                CLEAR_PUNISHMENTS_ROLE_IDS = [int(role_id.strip()) for role_id in CLEAR_PUNISHMENTS_ROLE_IDS_STR.split(',') if role_id.strip()]
            except ValueError:
                print("⚠️  Aviso: CLEAR_PUNISHMENTS_ROLE_IDS contém valores inválidos. Use IDs numéricos separados por vírgula.")
                CLEAR_PUNISHMENTS_ROLE_IDS = []
        
        # Tipos de arquivos de imagem aceitos
        VALID_IMAGE_TYPES = [
            'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
            'image/webp', 'image/bmp', 'image/tiff'
        ]
        
        # Extensões de arquivos de imagem aceitos
        VALID_IMAGE_EXTENSIONS = [
            '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'
        ]
    
    # Configurações de logs
    class Logging:
        """Configurações de logging."""
        
        # Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL) - Carregado do .env
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Formato das mensagens de log
        LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Arquivo de log (deixe vazio para não salvar em arquivo) - Carregado do .env
        LOG_FILE = os.getenv("LOG_FILE", "")  # Ex: "bot.log"


def validate_config():
    """Valida as configurações do bot."""
    errors = []
    
    if not BotConfig.BOT_TOKEN or BotConfig.BOT_TOKEN == "":
        errors.append("❌ Token do bot não configurado. Por favor, defina DISCORD_BOT_TOKEN no arquivo .env")
    
    if not BotConfig.TEST_GUILDS:
        errors.append("⚠️  IDs de servidores de teste não configurados. Por favor, defina TEST_GUILD_IDS no arquivo .env")
    
    if BotConfig.PunishmentSystem.TIMEOUT_MINUTES <= 0:
        errors.append("❌ TIMEOUT_MINUTES deve ser maior que 0")
    
    if BotConfig.PunishmentSystem.MAX_QUANTITY <= 0:
        errors.append("❌ MAX_QUANTITY deve ser maior que 0")
    
    if BotConfig.PunishmentSystem.MIN_QUANTITY <= 0:
        errors.append("❌ MIN_QUANTITY deve ser maior que 0")
    
    if BotConfig.PunishmentSystem.MIN_MOTIVO_LENGTH <= 0:
        errors.append("❌ MIN_MOTIVO_LENGTH deve ser maior que 0")
    
    return errors


if __name__ == "__main__":
    # Validação rápida das configurações
    errors = validate_config()
    
    if errors:
        print("⚠️  Erros de configuração encontrados:")
        for error in errors:
            print(f"  {error}")
        print("\n💡 Por favor, corrija as configurações antes de iniciar o bot.")
    else:
        print("✅ Configurações válidas!")