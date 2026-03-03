#!/usr/bin/env python3
"""
Gerenciador de Dados Persistentes

Este módulo gerencia o armazenamento e carregamento persistente de punições
e estados temporários do bot.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime


class DataManager:
    """
    Gerenciador de dados persistentes para o bot de punições.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Inicializa o gerenciador de dados.
        
        Args:
            data_dir: Diretório onde os arquivos de dados serão armazenados
        """
        self.data_dir = data_dir
        self.punishments_file = os.path.join(data_dir, "punishments.json")
        self.pending_file = os.path.join(data_dir, "pending.json")
        self.sessions_file = os.path.join(data_dir, "jj_sessions.json")
        
        # Configura o logger
        self.logger = logging.getLogger(__name__)
        
        # Cria o diretório de dados se não existir
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Cria o diretório de dados se não existir."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            self.logger.info(f"Diretório de dados criado: {self.data_dir}")
    
    def _load_json_file(self, file_path: str, default_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Carrega um arquivo JSON, criando-o com conteúdo padrão se não existir.
        
        Args:
            file_path: Caminho do arquivo JSON
            default_content: Conteúdo padrão para criar o arquivo
            
        Returns:
            Dict: Conteúdo do arquivo JSON
        """
        if not os.path.exists(file_path):
            # Cria arquivo com conteúdo padrão
            self._save_json_file(file_path, default_content)
            return default_content
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
            self.logger.error(f"Erro ao carregar {file_path}: {e}")
            # Retorna conteúdo padrão em caso de erro
            return default_content
    
    def _save_json_file(self, file_path: str, content: Dict[str, Any]):
        """
        Salva conteúdo em um arquivo JSON.
        
        Args:
            file_path: Caminho do arquivo JSON
            content: Conteúdo a ser salvo
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        except IOError as e:
            self.logger.error(f"Erro ao salvar {file_path}: {e}")
            raise
    
    def load_punishments(self) -> Dict[int, Dict]:
        """
        Carrega as punições persistentes do arquivo.
        
        Returns:
            Dict: Dicionário de punições {id: dados_da_punição}
        """
        data = self._load_json_file(
            self.punishments_file, 
            {"punishments": {}, "counter": 1}
        )
        
        # Converte as chaves de string para int (IDs das punições)
        punishments = {}
        for punishment_id, punishment_data in data.get("punishments", {}).items():
            try:
                punishments[int(punishment_id)] = punishment_data
            except ValueError:
                self.logger.warning(f"ID de punição inválido encontrado: {punishment_id}")
        
        counter = data.get("counter", 1)
        
        self.logger.info(f"Punições carregadas: {len(punishments)} registros, próximo ID: {counter}")
        return punishments, counter
    
    def save_punishments(self, punishments: Dict[int, Dict], counter: int):
        """
        Salva as punições no arquivo.
        
        Args:
            punishments: Dicionário de punições
            counter: Próximo ID a ser usado
        """
        # Converte as chaves de int para string para o JSON
        punishments_str_keys = {str(punishment_id): punishment_data 
                              for punishment_id, punishment_data in punishments.items()}
        
        data = {
            "punishments": punishments_str_keys,
            "counter": counter
        }
        
        self._save_json_file(self.punishments_file, data)
        self.logger.info(f"Punições salvas: {len(punishments)} registros, próximo ID: {counter}")
    
    def load_pending_punishments(self) -> Dict[int, Dict]:
        """
        Carrega os estados temporários de punições pendentes.
        
        Returns:
            Dict: Dicionário de punições pendentes {user_id: dados_do_estado}
        """
        data = self._load_json_file(self.pending_file, {})
        
        # Converte as chaves de string para int (IDs dos usuários)
        pending = {}
        for user_id, state_data in data.items():
            try:
                pending[int(user_id)] = state_data
            except ValueError:
                self.logger.warning(f"ID de usuário inválido encontrado: {user_id}")
        
        self.logger.info(f"Estados pendentes carregados: {len(pending)} registros")
        return pending
    
    def save_pending_punishments(self, pending_punishments: Dict[int, Dict]):
        """
        Salva os estados temporários de punições pendentes.
        
        Args:
            pending_punishments: Dicionário de estados pendentes
        """
        # Converte as chaves de int para string para o JSON
        pending_str_keys = {str(user_id): state_data 
                          for user_id, state_data in pending_punishments.items()}
        
        self._save_json_file(self.pending_file, pending_str_keys)
        self.logger.info(f"Estados pendentes salvos: {len(pending_punishments)} registros")
    
    def backup_punishments(self) -> str:
        """
        Cria um backup das punições com timestamp.
        
        Returns:
            str: Caminho do arquivo de backup criado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.data_dir, f"punishments_backup_{timestamp}.json")
        
        try:
            punishments, counter = self.load_punishments()
            self._save_json_file(backup_file, {"punishments": punishments, "counter": counter})
            self.logger.info(f"Backup criado: {backup_file}")
            return backup_file
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            return ""
    
    def clear_pending_punishments(self):
        """
        Limpa todos os estados pendentes (usado no início do bot).
        """
        self._save_json_file(self.pending_file, {})
        self.logger.info("Estados pendentes limpos")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas sobre os dados armazenados.
        
        Returns:
            Dict: Estatísticas sobre punições e estados
        """
        punishments, counter = self.load_punishments()
        pending = self.load_pending_punishments()
        
        # Conta status das punições
        status_count = {}
        total_jjs = 0
        
        for punishment_data in punishments.values():
            status = punishment_data.get("status", "desconhecido")
            status_count[status] = status_count.get(status, 0) + 1
            
            # Conta JJ's totais
            quantidade = punishment_data.get("quantidade", 0)
            if isinstance(quantidade, (int, float)):
                total_jjs += quantidade
        
        stats = {
            "total_punishments": len(punishments),
            "total_pending_states": len(pending),
            "next_id": counter,
            "status_distribution": status_count,
            "total_jjs_applied": total_jjs,
            "data_files": {
                "punishments": self.punishments_file,
                "pending": self.pending_file
            }
        }
        
        return stats


# Instância global do gerenciador de dados
data_manager = DataManager()