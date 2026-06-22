import sqlite3
from datetime import datetime
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

Base = declarative_base()

class Conta(Base):
    __tablename__ = 'contas'
    
    id = Column(Integer, primary_key=True)
    data_cadastro = Column(DateTime, default=datetime.now)
    vencimento = Column(String(10), nullable=False)
    fornecedor = Column(String(255), nullable=False)
    valor = Column(Float, nullable=False)
    categoria = Column(String(100), nullable=False)
    forma_pagamento = Column(String(50), nullable=False)
    codigo_pix_conta = Column(Text)
    status = Column(String(20), default='Pendente')
    observacoes = Column(Text)
    data_pagamento = Column(String(10))
    created_at = Column(DateTime, default=datetime.now)

class Comprovante(Base):
    __tablename__ = 'comprovantes'
    
    id = Column(Integer, primary_key=True)
    conta_id = Column(Integer, nullable=False)
    arquivo_nome = Column(String(255), nullable=False)
    arquivo_tipo = Column(String(50))
    arquivo_dados = Column(LargeBinary)
    arquivo_local_path = Column(String(500))
    arquivo_cloud_url = Column(String(500))
    data_upload = Column(DateTime, default=datetime.now)
    dados_extraidos = Column(Text)
    notas = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Categoria(Base):
    __tablename__ = 'categorias'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, nullable=False)

class BancoDados:
    def __init__(self, db_type='sqlite', db_file='contas.db', db_url=None):
        self.db_type = db_type
        
        if db_type == 'sqlite':
            self.engine = create_engine(f'sqlite:///{db_file}')
        elif db_type == 'postgresql':
            self.engine = create_engine(db_url)
        else:
            raise ValueError(f"Tipo de banco não suportado: {db_type}")
        
        self.Session = sessionmaker(bind=self.engine)
        self.criar_tabelas()
        self.inserir_categorias_padrao()
    
    def criar_tabelas(self):
        Base.metadata.create_all(self.engine)
        print("✅ Tabelas criadas/verificadas com sucesso")
    
    def inserir_categorias_padrao(self):
        session = self.Session()
        categorias = [
            'Condomínio',
            'IPTU',
            'Curso extra João',
            'Curso extra Gigi',
            'Cartão crédito visa BB',
            'Cartão crédito Mastercard BB',
            'Cartão crédito visa itaú',
            'Marina',
            'Marinheiro',
            'Babá',
            'Salário Edna',
            'Salário Vitor',
            'Gislaini',
            'Vale transporte Edna',
            'Condomínio Manso',
            'Ajuda Vovó',
            'CMSP',
            'Celular',
            'Cesari',
            'Outro'
        ]
        
        for cat_nome in categorias:
            existe = session.query(Categoria).filter_by(nome=cat_nome).first()
            if not existe:
                categoria = Categoria(nome=cat_nome)
                session.add(categoria)
        
        session.commit()
        session.close()
        print("✅ Categorias padrão inseridas")
    
    def adicionar_conta(self, vencimento, fornecedor, valor, categoria, forma_pagamento, codigo_pix=None, observacoes=None):
        session = self.Session()
        nova_conta = Conta(
            vencimento=vencimento,
            fornecedor=fornecedor,
            valor=valor,
            categoria=categoria,
            forma_pagamento=forma_pagamento,
            codigo_pix_conta=codigo_pix,
            observacoes=observacoes,
            status='Pendente'
        )
        session.add(nova_conta)
        session.commit()
        conta_id = nova_conta.id
        session.close()
        return conta_id
    
    def adicionar_comprovante(self, conta_id, arquivo_nome, arquivo_tipo, dados_arquivo, dados_extraidos=None, arquivo_local=None, arquivo_url=None):
        session = self.Session()
        comprovante = Comprovante(
            conta_id=conta_id,
            arquivo_nome=arquivo_nome,
            arquivo_tipo=arquivo_tipo,
            arquivo_dados=dados_arquivo,
            arquivo_local_path=arquivo_local,
            arquivo_cloud_url=arquivo_url,
            dados_extraidos=dados_extraidos
        )
        session.add(comprovante)
        session.commit()
        session.close()
        print(f"✅ Comprovante {arquivo_nome} armazenado para conta #{conta_id}")
    
    def obter_proximas_contas(self, dias=3):
        from datetime import date, timedelta
        hoje = date.today()
        limite = hoje + timedelta(days=dias)
        session = self.Session()
        contas = session.query(Conta).filter(Conta.status == 'Pendente').all()
        session.close()
        resultado = []
        for c in contas:
            try:
                venc = datetime.strptime(c.vencimento, '%d/%m/%Y').date()
                if hoje <= venc <= limite:
                    resultado.append(c)
            except Exception:
                pass
        return resultado
    
    def buscar_contas_por_valor(self, valor: float, tolerancia: float = 0.01):
        """Busca contas pendentes que correspondam ao valor do comprovante"""
        session = self.Session()
        contas = session.query(Conta).filter(Conta.status == 'Pendente').all()
        session.close()
        return [c for c in contas if abs(c.valor - valor) <= tolerancia]

    def obter_contas_por_categoria(self, categoria):
        session = self.Session()
        contas = session.query(Conta).filter(
            Conta.categoria == categoria,
            Conta.status.in_(['Pendente', 'Pago'])
        ).all()
        session.close()
        return contas
    
    def marcar_como_paga(self, conta_id, data_pagamento=None):
        session = self.Session()
        conta = session.query(Conta).filter_by(id=conta_id).first()
        if conta:
            conta.status = 'Pago'
            conta.data_pagamento = data_pagamento or datetime.now().strftime('%d/%m/%Y')
            session.commit()
            print(f"✅ Conta #{conta_id} marcada como paga")
        session.close()
    
    def obter_comprovante(self, conta_id):
        session = self.Session()
        comprovante = session.query(Comprovante).filter_by(conta_id=conta_id).first()
        session.close()
        return comprovante
    
    def listar_todas_contas(self):
        session = self.Session()
        contas = session.query(Conta).all()
        session.close()
        return contas

if __name__ == '__main__':
    db = BancoDados(db_type='sqlite', db_file='contas.db')
    print("✅ Banco de dados pronto para usar!")
